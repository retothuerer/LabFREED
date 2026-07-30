"""SignalsActionConsumer implements ActionConsumer on top of a SignalsInventoryClient-
shaped object. These tests use a hand-rolled fake client (not a mock of the real HTTP
client) - SignalsActionConsumer only depends on that interface
(find_container_id_by_field/get_container/get_location/set_container_location/
set_container_amount/dispose_container), never on requests/HTTP directly, so a fake
is the right unit boundary and no real Signals tenant is involved.

update_amount only accepts a small whitelist of volume units for now (see
developer-docs/TODO.md, "Real UCUM unit conversion for SignalsActionConsumer.update_amount")
- deliberately NOT "ML" as a synonym for "mL": UCUM is case-sensitive and "ML" means
  megalitre (mega- prefix + litre), a completely different quantity - conflating the
  two would silently misinterpret an amount by a factor of a billion.
"""
import pytest

from labfreed.labfreed_experimental.actions.consumers.signals_consumer import SignalsActionConsumer

PAC_ID = 'HTTPS://PAC.GIVAUDAN.COM/-MS/AMYLASE/9876'
LOCATION_PAC_ID = 'HTTPS://PAC.BUCHI.COM/-MD/C-950/FAKE0000'
LOCATION_ID = 'f6dd3e68-9344-4447-8b9c-3d23349b4ccb'
HOME_LOCATION_PAC_ID = 'HTTPS://PAC.GIVAUDAN.COM/-X/LAB1'
HOME_LOCATION_ID = '6e8634df-885f-40b1-8c96-bee264a41e44'
PAC_ID_FIELD_NAME = 'PAC-ID'
CONTAINER_ID = 'container-uuid-1'


class FakeSignalsClient:
    """Duck-types the bits of SignalsInventoryClient the consumer calls, backed by an
    in-memory container/location so behavior can be asserted without any HTTP."""

    def __init__(self, container=None, location_names=None):
        self.container = container
        self.location_names = location_names or {}
        self.calls = []

    def find_container_id_by_field(self, field_name, value, status=None):
        self.calls.append(('find_container_id_by_field', field_name, value, status))
        if self.container is None:
            return None
        return CONTAINER_ID

    def get_container(self, container_id):
        self.calls.append(('get_container', container_id))
        return self.container

    def get_location(self, location_id):
        self.calls.append(('get_location', location_id))
        return {'attributes': {'name': self.location_names.get(location_id, location_id)}}

    def set_container_location(self, container_id, location_id):
        self.calls.append(('set_container_location', container_id, location_id))
        self.container['attributes']['location']['id'] = location_id

    def set_container_amount(self, container_id, value_mL):
        self.calls.append(('set_container_amount', container_id, value_mL))
        self.container['attributes']['displayAmount'] = f'{value_mL} mL'

    def dispose_container(self, container_id):
        self.calls.append(('dispose_container', container_id))
        self.container['attributes']['status'] = 'DISPOSED'


def _container(location_id=HOME_LOCATION_ID, display_amount='250 mL'):
    return {'attributes': {'location': {'id': location_id}, 'displayAmount': display_amount, 'status': 'AVAILABLE'}}


def _consumer(client):
    return SignalsActionConsumer(
        client=client,
        pac_id_field_name=PAC_ID_FIELD_NAME,
        location_pac_ids={LOCATION_PAC_ID: LOCATION_ID, HOME_LOCATION_PAC_ID: HOME_LOCATION_ID},
    )


# ---------------------------------------------------------------------------
# update_location
# ---------------------------------------------------------------------------

def test_update_location_moves_the_container_and_reports_where_it_came_from():
    client = FakeSignalsClient(container=_container(location_id=HOME_LOCATION_ID),
                                location_names={LOCATION_ID: 'Chromatography System'})
    consumer = _consumer(client)

    result = consumer.update_location(PAC_ID, LOCATION_PAC_ID)

    assert result.ok is True
    assert result.previous_location_pac_id == HOME_LOCATION_PAC_ID
    assert result.location_name == 'Chromatography System'
    assert ('set_container_location', CONTAINER_ID, LOCATION_ID) in client.calls


def test_update_location_previous_location_is_none_when_it_was_somewhere_unmapped():
    client = FakeSignalsClient(container=_container(location_id='some-other-uuid-not-in-our-map'))
    consumer = _consumer(client)

    result = consumer.update_location(PAC_ID, LOCATION_PAC_ID)

    assert result.ok is True
    assert result.previous_location_pac_id is None


def test_update_location_container_not_found():
    client = FakeSignalsClient(container=None)
    consumer = _consumer(client)

    result = consumer.update_location(PAC_ID, LOCATION_PAC_ID)

    assert result.ok is False
    assert result.error
    assert not any(c[0] == 'set_container_location' for c in client.calls)


def test_update_location_unknown_location_pac_id_is_rejected_without_touching_signals():
    client = FakeSignalsClient(container=_container())
    consumer = _consumer(client)

    result = consumer.update_location(PAC_ID, 'HTTPS://PAC.UNKNOWN.COM/-X/NOWHERE')

    assert result.ok is False
    assert result.error
    assert client.calls == []


# ---------------------------------------------------------------------------
# update_amount
# ---------------------------------------------------------------------------

def test_update_amount_sets_a_plain_milliliter_amount():
    client = FakeSignalsClient(container=_container())
    consumer = _consumer(client)

    result = consumer.update_amount(PAC_ID, '250 mL')

    assert result.ok is True
    assert ('set_container_amount', CONTAINER_ID, 250.0) in client.calls
    assert result.display_amount == '250.0 mL'


def test_update_amount_converts_liters_to_milliliters():
    client = FakeSignalsClient(container=_container())
    consumer = _consumer(client)

    result = consumer.update_amount(PAC_ID, '1 L')

    assert result.ok is True
    assert ('set_container_amount', CONTAINER_ID, 1000.0) in client.calls


def test_update_amount_rejects_a_non_volume_unit():
    client = FakeSignalsClient(container=_container())
    consumer = _consumer(client)

    result = consumer.update_amount(PAC_ID, '5 g')

    assert result.ok is False
    assert result.error
    assert client.calls == []


def test_update_amount_rejects_megaliters_rather_than_treating_them_as_milliliters():
    """Guards the exact case-sensitivity bug described in the module docstring."""
    client = FakeSignalsClient(container=_container())
    consumer = _consumer(client)

    result = consumer.update_amount(PAC_ID, '5 ML')

    assert result.ok is False
    assert client.calls == []


def test_update_amount_rejects_zero_and_points_at_container_is_empty():
    client = FakeSignalsClient(container=_container())
    consumer = _consumer(client)

    result = consumer.update_amount(PAC_ID, '0 mL')

    assert result.ok is False
    assert 'container_is_empty' in result.error
    assert client.calls == []


def test_update_amount_container_not_found():
    client = FakeSignalsClient(container=None)
    consumer = _consumer(client)

    result = consumer.update_amount(PAC_ID, '250 mL')

    assert result.ok is False
    assert not any(c[0] == 'set_container_amount' for c in client.calls)


# ---------------------------------------------------------------------------
# container_is_empty
# ---------------------------------------------------------------------------

def test_container_is_empty_disposes_the_container():
    client = FakeSignalsClient(container=_container())
    consumer = _consumer(client)

    result = consumer.container_is_empty(PAC_ID)

    assert result.ok is True
    assert result.disposed is True
    assert ('dispose_container', CONTAINER_ID) in client.calls


def test_container_is_empty_container_not_found():
    client = FakeSignalsClient(container=None)
    consumer = _consumer(client)

    result = consumer.container_is_empty(PAC_ID)

    assert result.ok is False
    assert not any(c[0] == 'dispose_container' for c in client.calls)

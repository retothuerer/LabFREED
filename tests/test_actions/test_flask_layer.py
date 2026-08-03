"""create_actions_blueprint() wires the three well-known actions up as POST routes
that read their parameters from the query string, appended by the caller on top of
the resolved CIT url (see developer-docs/design-choices.md, "Well-known action
handler: action-generic params travel as plain query params, not through the CIT
template", for why there's no other mechanism today) and dispatch to whatever
ActionBackend it's given. These tests use a fake, in-memory backend (no real Signals
Notebook involved) built via Flask's own test_client(), the same way
tests/test_attributes/test_attribute_server_factory.py already tests the sibling
attribute-server Flask layer.
"""
import pytest
from flask import Flask

from labfreed.labfreed_experimental.actions.backend import (
    ContainerIsEmptyResult,
    UpdateAmountResult,
    UpdateLocationResult,
)
from labfreed.labfreed_experimental.actions.flask_layer import create_actions_blueprint

PAC_ID = 'HTTPS://PAC.GIVAUDAN.COM/-MS/AMYLASE/9876'
LOCATION_PAC_ID = 'HTTPS://PAC.BUCHI.COM/-MD/C-950/FAKE0000'


class FakeBackend:
    """Records every call it receives and returns whatever result was queued for it."""

    def __init__(self):
        self.calls = []
        self.update_location_result = UpdateLocationResult(ok=True, previous_location_pac_id=None, location_name='Lab1')
        self.update_amount_result = UpdateAmountResult(ok=True, display_amount='250 mL')
        self.container_is_empty_result = ContainerIsEmptyResult(ok=True, disposed=True)

    def update_location(self, pac_id, location_pac_id):
        self.calls.append(('update_location', pac_id, location_pac_id))
        return self.update_location_result

    def update_amount(self, pac_id, quantity):
        self.calls.append(('update_amount', pac_id, quantity))
        return self.update_amount_result

    def container_is_empty(self, pac_id):
        self.calls.append(('container_is_empty', pac_id))
        return self.container_is_empty_result


def _build_test_client(backend):
    app = Flask(__name__)
    app.register_blueprint(create_actions_blueprint(backend))
    return app.test_client()


def test_update_location_dispatches_to_the_backend_with_both_pac_ids():
    backend = FakeBackend()
    client = _build_test_client(backend)

    resp = client.post('/actions/update_location', query_string={'pac_id': PAC_ID, 'location': LOCATION_PAC_ID})

    assert resp.status_code == 200
    assert resp.get_json() == backend.update_location_result.model_dump()
    assert backend.calls == [('update_location', PAC_ID, LOCATION_PAC_ID)]


def test_update_amount_dispatches_to_the_backend_with_the_quantity_string():
    backend = FakeBackend()
    client = _build_test_client(backend)

    resp = client.post('/actions/update_amount', query_string={'pac_id': PAC_ID, 'amount': '250 mL'})

    assert resp.status_code == 200
    assert resp.get_json() == backend.update_amount_result.model_dump()
    assert backend.calls == [('update_amount', PAC_ID, '250 mL')]


def test_container_is_empty_dispatches_to_the_backend_with_just_the_pac_id():
    backend = FakeBackend()
    client = _build_test_client(backend)

    resp = client.post('/actions/container_is_empty', query_string={'pac_id': PAC_ID})

    assert resp.status_code == 200
    assert resp.get_json() == backend.container_is_empty_result.model_dump()
    assert backend.calls == [('container_is_empty', PAC_ID)]


def test_a_backend_reported_failure_still_comes_back_as_200_with_ok_false():
    """The JSON envelope (ok/error) is the error channel, not the HTTP status - a
    caller always gets a 200 with a body it can inspect, whether the action
    succeeded or not."""
    backend = FakeBackend()
    backend.update_location_result = UpdateLocationResult(ok=False, error="no AVAILABLE container found")
    client = _build_test_client(backend)

    resp = client.post('/actions/update_location', query_string={'pac_id': PAC_ID, 'location': LOCATION_PAC_ID})

    assert resp.status_code == 200
    assert resp.get_json() == {'ok': False, 'error': 'no AVAILABLE container found',
                                'previous_location_pac_id': None, 'location_name': None}


def test_missing_pac_id_is_a_400_and_never_reaches_the_backend():
    backend = FakeBackend()
    client = _build_test_client(backend)

    resp = client.post('/actions/update_amount', query_string={'amount': '250 mL'})

    assert resp.status_code == 400
    assert backend.calls == []

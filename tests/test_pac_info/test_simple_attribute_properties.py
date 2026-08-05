import pytest

from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup, Reference
from labfreed.pac_attributes.well_known_attribute_keys import CommercePackagingKeys, IdentifierKeys, RegulatorySafetyKeys
from labfreed.pac_id import IDSegment, PAC_ID
from labfreed.utilities.quantity import Quantity
from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo


def _pac_id():
    return PAC_ID(issuer='METTORIUS.COM', identifier=[IDSegment(value='-DR'), IDSegment(value='999')])


def _pac_info(attributes: list[Attribute]) -> PacInfo:
    group = AttributeGroup(
        group_key='g1',
        attributes={a.key: a for a in attributes},
        origin='test',
        language='en',
    )
    return PacInfo(pac_id=_pac_id(), attribute_groups={'g1': group})


def test_supplier_returns_the_reference_attribute_when_present():
    # SUPPLIER's value is expected to be a PAC-ID reference to the supplier's own
    # attribute page (name/address/phone live there), not inline contact info -
    # see design-choices.md
    pac_info = _pac_info([
        Attribute(key=IdentifierKeys.SUPPLIER, values=Reference('HTTPS://PAC.SUPPLIER.COM/-MD/240:X')),
    ])
    assert isinstance(pac_info.supplier.values, Reference)
    assert pac_info.supplier.values.root == 'HTTPS://PAC.SUPPLIER.COM/-MD/240:X'


def test_supplier_is_none_when_absent():
    assert _pac_info([]).supplier is None


@pytest.mark.skip(reason="NOT REVIEWED")
def test_nominal_quantity_returns_the_attribute_when_present():
    pac_info = _pac_info([Attribute(key=CommercePackagingKeys.QUANTITY, values=Quantity(value=500, unit='mL'))])
    assert pac_info.nominal_quantity.values == Quantity(value=500, unit='mL')


def test_nominal_quantity_is_none_when_absent():
    assert _pac_info([]).nominal_quantity is None


def test_ufi_returns_the_attribute_when_present():
    pac_info = _pac_info([Attribute(key=RegulatorySafetyKeys.UNIQUE_FORMULA_IDENTIFIER, values='XXXX-XXXX-XXXX-XXXX')])
    assert pac_info.ufi.values == 'XXXX-XXXX-XXXX-XXXX'


def test_ufi_is_none_when_absent():
    assert _pac_info([]).ufi is None

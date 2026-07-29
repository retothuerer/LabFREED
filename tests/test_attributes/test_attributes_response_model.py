import json

import pytest

from labfreed.pac_attributes.api_data_models.response import (
    AttributeResponsePayload,
    AttributesOfItem,
    AttributesOfPACID,
    NumericAttributeItemsElement,
)

PAC_ID_STR = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234"


def test_numeric_attribute_accepts_compound_ucum_unit():
    # today's regex-based _validate_unit only loosely checks UCUM syntax and has no notion of
    # compound units being "real" - this pins that a valid compound unit produces no error once
    # validation shares ucum_bridge.is_valid_ucum.
    e = NumericAttributeItemsElement(value="12.5 kg/m3")
    assert not e.errors()


def test_numeric_attribute_rejects_caret_exponent_without_units_extra(without_ucum_support):
    # '^' for exponents is a common mistake (should be e.g. 'm2' or 'm-2') - the no-dependency
    # fallback path must still reject it on its own (is_valid_ucum's own tests cover the
    # authoritative, library-backed path for the same case).
    e = NumericAttributeItemsElement(value="12.5 m^2")
    assert e.errors()


def test_attributes_of_item_serializes_with_id_field_per_spec():
    # PAC-ID-Attributes spec commit "iri instead of pac-id" renamed the response
    # payload's field from pac_id to id - this pins the wire format to that rename.
    item = AttributesOfItem(id=PAC_ID_STR, attribute_groups=[])
    dumped = json.loads(item.model_dump_json())
    assert dumped["id"] == PAC_ID_STR
    assert "pac_id" not in dumped


def test_attribute_response_payload_data_uses_id_field():
    payload = AttributeResponsePayload(language="en", data=[AttributesOfItem(id=PAC_ID_STR, attribute_groups=[])])
    dumped = json.loads(payload.to_json())
    assert dumped["data"][0]["id"] == PAC_ID_STR


def test_attributes_of_pacid_is_deprecated_but_still_constructible():
    with pytest.deprecated_call():
        item = AttributesOfPACID(id=PAC_ID_STR, attribute_groups=[])
    assert item.id == PAC_ID_STR


def test_attributes_of_pacid_accepts_legacy_pac_id_kwarg():
    with pytest.deprecated_call():
        item = AttributesOfPACID(pac_id=PAC_ID_STR, attribute_groups=[])
    assert item.id == PAC_ID_STR


def test_attributes_of_pacid_pac_id_property_still_works_and_warns():
    with pytest.deprecated_call():
        item = AttributesOfPACID(id=PAC_ID_STR, attribute_groups=[])
    with pytest.deprecated_call():
        assert item.pac_id == PAC_ID_STR

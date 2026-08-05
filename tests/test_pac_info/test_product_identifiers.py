import pytest

from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup
from labfreed.pac_attributes.well_known_attribute_keys import IdentifierKeys, RegulatorySafetyKeys
from labfreed.pac_id import IDSegment, PAC_ID
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


def test_product_identifiers_is_empty_when_none_present():
    assert _pac_info([]).product_identifiers == []


def test_product_identifiers_collects_whichever_identifier_keys_are_present():
    pac_info = _pac_info([
        Attribute(key=IdentifierKeys.CAS_NUMBER, values='64-17-5'),
        Attribute(key=IdentifierKeys.EC_NUMBER, values='200-578-6'),
    ])
    keys = {a.key for a in pac_info.product_identifiers}
    assert keys == {IdentifierKeys.CAS_NUMBER.value, IdentifierKeys.EC_NUMBER.value}


def test_product_identifiers_orders_clp_annex_vi_index_first():
    # CLP-specific identity (Annex VI index no.) is the most authoritative for a
    # notified substance, so it's listed ahead of the generic CAS/EC/product-code
    # identifiers when several are present at once.
    pac_info = _pac_info([
        Attribute(key=IdentifierKeys.CAS_NUMBER, values='64-17-5'),
        Attribute(key=RegulatorySafetyKeys.CLP_ANNEX_VI_INDEX_NO, values='603-002-00-5'),
    ])
    assert [a.key for a in pac_info.product_identifiers] == [
        RegulatorySafetyKeys.CLP_ANNEX_VI_INDEX_NO.value,
        IdentifierKeys.CAS_NUMBER.value,
    ]


def test_product_identifiers_does_not_include_display_name():
    # trade name is display_name's job, not product_identifiers' - see design-choices.md
    pac_info = _pac_info([Attribute(key=IdentifierKeys.CAS_NUMBER, values='64-17-5')])
    assert all(a.key != 'https://schema.org/name' for a in pac_info.product_identifiers)

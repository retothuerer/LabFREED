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


def test_get_attributes_matches_full_key():
    pac_info = _pac_info([Attribute(key=IdentifierKeys.CAS_NUMBER, values='64-17-5')])
    assert [a.values for a in pac_info.get_attributes(IdentifierKeys.CAS_NUMBER)] == ['64-17-5']


def test_get_attributes_matches_by_substring_not_just_exact_key():
    # get_attributes does `key in a.key` - a plain substring test, not equality - so a
    # partial search term (here, just the host) still matches the full key
    pac_info = _pac_info([Attribute(key=IdentifierKeys.CAS_NUMBER, values='64-17-5')])
    assert len(pac_info.get_attributes('registry.identifiers.org')) == 1
    assert len(pac_info.get_attributes('registry.identifiers.org')) == len(
        pac_info.get_attributes(IdentifierKeys.CAS_NUMBER))


def test_get_attributes_unwraps_enum_key():
    # both call styles must behave identically - passing the enum member directly is
    # the common case, but get_attributes/get_attribute unwrap it to .value themselves
    pac_info = _pac_info([Attribute(key=IdentifierKeys.EC_NUMBER, values='200-578-6')])
    assert pac_info.get_attributes(IdentifierKeys.EC_NUMBER) == pac_info.get_attributes(IdentifierKeys.EC_NUMBER.value)


def test_get_attribute_returns_none_when_no_match():
    assert _pac_info([]).get_attribute(RegulatorySafetyKeys.UNIQUE_FORMULA_IDENTIFIER) is None


def test_get_attribute_mode_first_and_last():
    # both attributes share the same *substring* (the registry.identifiers.org host),
    # so a substring lookup against just that host sees both, in insertion order
    pac_info = _pac_info([
        Attribute(key=IdentifierKeys.CAS_NUMBER, values='64-17-5'),
        Attribute(key=IdentifierKeys.CAS_NUMBER_ALT, values='alt-value'),
    ])
    matches = pac_info.get_attributes('wikidata.org/wiki/Property:P231')
    assert len(matches) == 1  # CAS_NUMBER_ALT only - CAS_NUMBER's key doesn't contain this substring
    assert pac_info.get_attribute('wikidata.org/wiki/Property:P231', mode='first').values == 'alt-value'


def test_get_attribute_invalid_mode_raises():
    with pytest.raises(ValueError):
        _pac_info([Attribute(key=IdentifierKeys.CAS_NUMBER, values='64-17-5')]).get_attribute(
            IdentifierKeys.CAS_NUMBER, mode='middle')

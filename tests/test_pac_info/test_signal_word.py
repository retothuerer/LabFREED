import pytest

from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup
from labfreed.pac_attributes.well_known_attribute_keys import RegulatorySafetyKeys
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


def test_signal_word_uses_explicit_attribute_when_present():
    # an explicit GHS_SIGNAL_WORD attribute is supplier-authoritative and wins even
    # though it doesn't match the severity implied by the hazard statement
    pac_info = _pac_info([
        Attribute(key=RegulatorySafetyKeys.GHS_SIGNAL_WORD, values='Warning'),
        Attribute(key=RegulatorySafetyKeys.GHS_HAZARD_STATEMENT, values='H300'),  # Danger
    ])
    # signal_word returns the plain value, not the Attribute wrapper
    assert pac_info.signal_word == 'Warning'


def test_signal_word_derived_from_hazard_statements_when_no_explicit_attribute():
    pac_info = _pac_info([
        Attribute(key=RegulatorySafetyKeys.GHS_HAZARD_STATEMENT, values='H410'),
    ])
    assert pac_info.signal_word == 'Warning'


def test_signal_word_derived_picks_most_severe_across_multiple_hazard_statements():
    pac_info = _pac_info([
        Attribute(key=RegulatorySafetyKeys.GHS_HAZARD_STATEMENT, values=['H410', 'H300']),
    ])
    assert pac_info.signal_word == 'Danger'


def test_signal_word_is_none_without_explicit_attribute_or_hazard_statements():
    pac_info = _pac_info([])
    assert pac_info.signal_word is None

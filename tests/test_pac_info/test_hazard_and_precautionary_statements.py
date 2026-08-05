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


def test_hazard_statements_resolves_predefined_text_and_completeness():
    pac_info = _pac_info([Attribute(key=RegulatorySafetyKeys.GHS_HAZARD_STATEMENT, values='H225')])
    statements = pac_info.hazard_statements
    assert len(statements) == 1
    statement = statements[0]
    assert statement.code == 'H225'
    assert statement.text == 'Highly flammable liquid and vapour'
    assert statement.text_origin == 'Predefined'
    assert statement.complete is True


def test_hazard_statements_is_sorted_by_code_and_deduplicated():
    pac_info = _pac_info([
        Attribute(key=RegulatorySafetyKeys.GHS_HAZARD_STATEMENT, values=['H319', 'H225', 'H225']),
    ])
    assert [s.code for s in pac_info.hazard_statements] == ['H225', 'H319']


def test_hazard_statements_ignores_precautionary_codes_mixed_into_the_same_value():
    pac_info = _pac_info([
        Attribute(key=RegulatorySafetyKeys.GHS_HAZARD_STATEMENT, values='H225 P210'),
    ])
    assert [s.code for s in pac_info.hazard_statements] == ['H225']


def test_precautionary_statements_resolves_predefined_text_and_completeness():
    pac_info = _pac_info([Attribute(key=RegulatorySafetyKeys.GHS_PRECAUTIONARY_STATEMENT, values='P210')])
    statements = pac_info.precautionary_statements
    assert len(statements) == 1
    assert statements[0].code == 'P210'
    assert statements[0].complete is True

def test_precautionary_statements_incomplete_when_annex_3_has_a_placeholder():
    # P264 "Wash ... thoroughly after handling." still has a supplier-completed
    # blank in the official text
    pac_info = _pac_info([Attribute(key=RegulatorySafetyKeys.GHS_PRECAUTIONARY_STATEMENT, values='P264')])
    assert pac_info.precautionary_statements[0].complete is False


def test_precautionary_statements_ignores_hazard_codes_mixed_into_the_same_value():
    pac_info = _pac_info([
        Attribute(key=RegulatorySafetyKeys.GHS_PRECAUTIONARY_STATEMENT, values='H225 P210'),
    ])
    assert [s.code for s in pac_info.precautionary_statements] == ['P210']

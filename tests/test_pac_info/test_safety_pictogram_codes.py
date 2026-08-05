import pytest

from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup, Resource
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


def test_safety_pictogram_codes_is_empty_when_nothing_present():
    assert _pac_info([]).safety_pictogram_codes == []


def test_safety_pictogram_codes_includes_explicitly_supplied_codes():
    pac_info = _pac_info([Attribute(key=RegulatorySafetyKeys.GHS_PICTOGRAM, values='GHS07')])
    assert pac_info.safety_pictogram_codes == ['GHS07']


def test_safety_pictogram_codes_derives_codes_from_hazard_statements():
    # H225 (Flammable liquids cat. 2) -> GHS02 (Flame), via the Annex 3 lookup table
    pac_info = _pac_info([Attribute(key=RegulatorySafetyKeys.GHS_HAZARD_STATEMENT, values='H225')])
    assert pac_info.safety_pictogram_codes == ['GHS02']


def test_safety_pictogram_codes_merges_explicit_and_derived_without_duplicates():
    pac_info = _pac_info([
        Attribute(key=RegulatorySafetyKeys.GHS_PICTOGRAM, values='GHS02'),  # already implied by H225 below
        Attribute(key=RegulatorySafetyKeys.GHS_HAZARD_STATEMENT, values=['H225', 'H319']),  # H319 -> GHS07
    ])
    assert pac_info.safety_pictogram_codes == ['GHS02', 'GHS07']


def test_safety_pictogram_codes_ignores_precautionary_statements():
    # precautionary statements carry no pictogram/signal-word classification at all
    pac_info = _pac_info([Attribute(key=RegulatorySafetyKeys.GHS_PRECAUTIONARY_STATEMENT, values='P210')])
    assert pac_info.safety_pictogram_codes == []


def test_explicit_pictogram_image_urls_collects_resource_values_only():
    pac_info = _pac_info([
        Attribute(key=RegulatorySafetyKeys.GHS_PICTOGRAM, values=[
            'GHS02',
            Resource('https://example.com/custom-flame.png'),
        ]),
    ])
    assert pac_info.explicit_pictogram_image_urls == ['https://example.com/custom-flame.png']


def test_explicit_pictogram_image_urls_is_empty_for_bare_codes():
    pac_info = _pac_info([Attribute(key=RegulatorySafetyKeys.GHS_PICTOGRAM, values='GHS02')])
    assert pac_info.explicit_pictogram_image_urls == []

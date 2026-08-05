import pytest

from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup
from labfreed.pac_attributes.well_known_attribute_keys import MetaAttributeKeys
from labfreed.pac_cat import PAC_CAT
from labfreed.pac_id import IDSegment, PAC_ID
from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo


def _pac_id():
    return PAC_ID(issuer='METTORIUS.COM', identifier=[IDSegment(value='-DR'), IDSegment(value='999')])


def _pac_cat(url_tail):
    return PAC_CAT.from_url(f'HTTPS://PAC.METTORIUS.COM/{url_tail}', suppress_validation_errors=True)


def _pac_info(pac_id=None, attributes: list[Attribute] = ()) -> PacInfo:
    group = AttributeGroup(
        group_key='g1',
        attributes={a.key: a for a in attributes},
        origin='test',
        language='en',
    )
    return PacInfo(pac_id=pac_id or _pac_id(), attribute_groups={'g1': group})


def test_display_name_is_none_with_nothing_to_derive_it_from():
    assert _pac_info().display_name is None


def test_display_name_uses_the_displayname_attribute_when_present():
    pac_info = _pac_info(attributes=[Attribute(key=MetaAttributeKeys.DISPLAYNAME, values='Acetone')])
    assert pac_info.display_name == 'Acetone'


def test_display_name_falls_back_to_the_240_category_segment():
    # PAC-CAT's 240 segment ("model/type") stands in for a display name when nothing
    # more specific (extension 'N' or the DISPLAYNAME attribute) is available
    pac_info = _pac_info(pac_id=_pac_cat('-MD/240:BAL500/21:12345'))
    assert pac_info.display_name == 'BAL500'


def test_display_name_attribute_wins_over_the_240_category_segment():
    pac_info = _pac_info(
        pac_id=_pac_cat('-MD/240:BAL500/21:12345'),
        attributes=[Attribute(key=MetaAttributeKeys.DISPLAYNAME, values='Acetone')],
    )
    assert pac_info.display_name == 'Acetone'

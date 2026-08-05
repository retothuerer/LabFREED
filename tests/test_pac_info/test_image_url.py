import pytest

from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup, Resource
from labfreed.pac_attributes.well_known_attribute_keys import MetaAttributeKeys
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


def test_image_url_is_none_when_absent():
    assert _pac_info([]).image_url is None


def test_image_url_unwraps_a_resource_value():
    pac_info = _pac_info([Attribute(key=MetaAttributeKeys.IMAGE, values=Resource('https://example.com/img.png'))])
    assert pac_info.image_url == 'https://example.com/img.png'


def test_image_url_accepts_a_plain_string_value():
    pac_info = _pac_info([Attribute(key=MetaAttributeKeys.IMAGE, values='https://example.com/img.png')])
    assert pac_info.image_url == 'https://example.com/img.png'

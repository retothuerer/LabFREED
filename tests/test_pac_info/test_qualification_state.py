import pytest

from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup
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


def test_qualification_state_returns_the_attribute_when_present():
    pac_info = _pac_info([
        Attribute(key='https://labfreed.org/qualification/status', values='qualified'),
    ])
    assert pac_info.qualification_state.values == 'qualified'


def test_qualification_state_is_none_when_absent():
    assert _pac_info([]).qualification_state is None

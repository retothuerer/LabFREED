import pytest

from labfreed.pac_id import IDSegment, PAC_ID
from labfreed.pac_id_resolver.services import Service, ServiceGroup
from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo


def _pac_id():
    return PAC_ID(issuer='METTORIUS.COM', identifier=[IDSegment(value='-DR'), IDSegment(value='999')])


def _service(service_name, application_intents, key=None, url='https://example.com') -> Service:
    return Service(service_name=service_name, application_intents=application_intents,
                    service_type='document', url=url, key=key)


def _pac_info(user_handovers=(), actions=()) -> PacInfo:
    return PacInfo(pac_id=_pac_id(), user_handovers=list(user_handovers), actions=list(actions))


def test_get_user_handovers_by_intent_exact_match_only_by_default():
    manual = _service('User Manual', ['document-operation-manual'])
    pac_info = _pac_info(user_handovers=[ServiceGroup(origin='test', services=[manual])])
    assert pac_info.get_user_handovers_by_intent('document') == []
    assert pac_info.get_user_handovers_by_intent('document-operation-manual') == [manual]


def test_get_user_handovers_by_intent_partial_match():
    manual = _service('User Manual', ['document-operation-manual'])
    pac_info = _pac_info(user_handovers=[ServiceGroup(origin='test', services=[manual])])
    assert pac_info.get_user_handovers_by_intent('document', partial_match=True) == [manual]


def test_get_user_handover_by_intent_mode_first_and_last():
    first = _service('First', ['important'])
    last = _service('Last', ['important'])
    pac_info = _pac_info(user_handovers=[ServiceGroup(origin='test', services=[first, last])])
    assert pac_info.get_user_handover_by_intent('important', mode='first') is first
    assert pac_info.get_user_handover_by_intent('important', mode='last') is last


def test_get_user_handover_by_intent_is_none_without_a_match():
    assert _pac_info().get_user_handover_by_intent('important') is None


def test_important_handovers_is_a_shortcut_for_the_important_intent():
    svc = _service('Something Important', ['important'])
    other = _service('Something Else', ['other'])
    pac_info = _pac_info(user_handovers=[ServiceGroup(origin='test', services=[svc, other])])
    assert pac_info.important_handovers == [svc]


def test_get_user_handovers_by_key_is_an_exact_match_never_partial():
    # key is an IRI-anchored vocabulary term, unlike the dash-separated intent strings -
    # no partial_match option exists for it at all
    sds = _service('SDS', ['document'], key='https://www.wikidata.org/wiki/Q222067')
    pac_info = _pac_info(user_handovers=[ServiceGroup(origin='test', services=[sds])])
    assert pac_info.get_user_handovers_by_key('https://www.wikidata.org/wiki/Q222067') == [sds]
    assert pac_info.get_user_handovers_by_key('wikidata.org') == []


def test_get_user_handovers_by_key_unwraps_enum():
    from labfreed.pac_attributes.well_known_attribute_keys import DocumentKeys
    sds = _service('SDS', ['document'], key=DocumentKeys.SAFETY_DATA_SHEET)
    pac_info = _pac_info(user_handovers=[ServiceGroup(origin='test', services=[sds])])
    assert pac_info.get_user_handovers_by_key(DocumentKeys.SAFETY_DATA_SHEET) == [sds]


def test_actions_mirror_handovers_by_intent_and_key():
    # get_action(s)_by_intent/key and important_actions are the same shape as their
    # user_handovers counterparts, just backed by PacInfo.actions instead
    act = _service('Reorder', ['important'], key='https://example.com/action/reorder')
    pac_info = _pac_info(actions=[ServiceGroup(origin='test', services=[act])])
    assert pac_info.get_actions_by_intent('important') == [act]
    assert pac_info.get_action_by_intent('important') is act
    assert pac_info.important_actions == [act]
    assert pac_info.get_actions_by_key('https://example.com/action/reorder') == [act]
    assert pac_info.get_action_by_key('https://example.com/action/reorder') is act

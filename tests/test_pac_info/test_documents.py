import pytest

from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup, Resource
from labfreed.pac_attributes.well_known_attribute_keys import DocumentKeys
from labfreed.pac_id import IDSegment, PAC_ID
from labfreed.pac_id_resolver.services import Service, ServiceGroup
from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo


def _pac_id():
    return PAC_ID(issuer='METTORIUS.COM', identifier=[IDSegment(value='-DR'), IDSegment(value='999')])


def _pac_info(attributes: list[Attribute] = (), user_handovers: list[ServiceGroup] = ()) -> PacInfo:
    group = AttributeGroup(
        group_key='g1',
        attributes={a.key: a for a in attributes},
        origin='test',
        language='en',
    )
    return PacInfo(pac_id=_pac_id(), attribute_groups={'g1': group}, user_handovers=list(user_handovers))


def _service(key, url) -> Service:
    return Service(service_name='Safety Data Sheet', application_intents=['document'],
                    service_type='document', url=url, key=key)


# safety_data_sheet and certificate_of_analysis both go through PacInfo._get_document:
# an attribute (Resource value) wins if present, a user handover Service keyed the
# same way is the fallback, and either maps into a uniform Document(name, key, url) -
# see design-choices.md and the earlier hazard-statement precedence decision this
# mirrors (attribute-delivered data outranks anything we'd otherwise derive/fetch).

def test_safety_data_sheet_prefers_attribute_over_user_handover():
    pac_info = _pac_info(
        attributes=[Attribute(key=DocumentKeys.SAFETY_DATA_SHEET, label='SDS (EN)',
                               values=Resource('https://example.com/attribute-sds.pdf'))],
        user_handovers=[ServiceGroup(origin='test', services=[
            _service(DocumentKeys.SAFETY_DATA_SHEET, 'https://example.com/handover-sds.pdf'),
        ])],
    )
    doc = pac_info.safety_data_sheet
    assert doc.name == 'SDS (EN)'
    assert doc.url == 'https://example.com/attribute-sds.pdf'


def test_safety_data_sheet_falls_back_to_user_handover_when_no_attribute():
    pac_info = _pac_info(user_handovers=[ServiceGroup(origin='test', services=[
        _service(DocumentKeys.SAFETY_DATA_SHEET, 'https://example.com/handover-sds.pdf'),
    ])])
    doc = pac_info.safety_data_sheet
    assert doc.name == 'Safety Data Sheet'
    assert doc.url == 'https://example.com/handover-sds.pdf'


def test_safety_data_sheet_is_none_when_neither_source_has_it():
    assert _pac_info().safety_data_sheet is None


def test_certificate_of_analysis_prefers_attribute_over_user_handover():
    pac_info = _pac_info(
        attributes=[Attribute(key=DocumentKeys.CERTIFICATE_OF_ANALYSIS, label='CoA (EN)',
                               values=Resource('https://example.com/attribute-coa.pdf'))],
        user_handovers=[ServiceGroup(origin='test', services=[
            _service(DocumentKeys.CERTIFICATE_OF_ANALYSIS, 'https://example.com/handover-coa.pdf'),
        ])],
    )
    doc = pac_info.certificate_of_analysis
    assert doc.name == 'CoA (EN)'
    assert doc.url == 'https://example.com/attribute-coa.pdf'


def test_certificate_of_analysis_falls_back_to_user_handover_when_no_attribute():
    pac_info = _pac_info(user_handovers=[ServiceGroup(origin='test', services=[
        _service(DocumentKeys.CERTIFICATE_OF_ANALYSIS, 'https://example.com/coa.pdf'),
    ])])
    assert pac_info.certificate_of_analysis.url == 'https://example.com/coa.pdf'


def test_certificate_of_analysis_is_none_when_absent():
    assert _pac_info().certificate_of_analysis is None

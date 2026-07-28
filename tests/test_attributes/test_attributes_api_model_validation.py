from pydantic import ValidationError
import pytest
from labfreed.labfreed_infrastructure import LabFREED_ValidationError
from labfreed.pac_attributes.api_data_models.request import AttributeRequestData

dummy_pac = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234'
trailing_slash_pac = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234/'
generic_iri = 'https://example.com/thing?x=1'
non_ascii_pac_chars = 'HTTPS://PAC.METTORIUS.COM/-£MD/BAL500/1234'
not_an_iri = 'not a url at all'


def test_valid_pac_id_is_accepted_with_no_warning():
    r = AttributeRequestData(subject_id=dummy_pac)
    assert r.is_valid
    assert not r.validation_messages()


def test_trailing_slash_pac_id_is_accepted_as_iri_with_warning():
    # per the PAC-ID-Attributes spec, subject_id only has to be an IRI, "preferably" a
    # PAC-ID - a PAC-ID-shaped id with an empty (trailing-slash) segment is a valid IRI
    # even though it isn't a strictly valid PAC-ID.
    r = AttributeRequestData(subject_id=trailing_slash_pac)
    assert r.is_valid
    assert any('not a valid PAC-ID' in m.msg for m in r.validation_messages())


def test_generic_non_pac_id_iri_is_accepted_with_warning():
    r = AttributeRequestData(subject_id=generic_iri)
    assert r.is_valid
    assert any('not a valid PAC-ID' in m.msg for m in r.validation_messages())


def test_non_ascii_pac_id_chars_are_now_accepted_as_iri():
    # historically this raised outright (characters not valid in a PAC-ID id segment);
    # since subject_id no longer has to be a strict PAC-ID, characters that are invalid
    # for a PAC-ID but valid in an IRI are now accepted, downgraded to a WARNING.
    r = AttributeRequestData(subject_id=non_ascii_pac_chars)
    assert r.is_valid
    assert any('not a valid PAC-ID' in m.msg for m in r.validation_messages())


def test_not_a_valid_iri_is_rejected():
    with pytest.raises((LabFREED_ValidationError, ValidationError)):
        AttributeRequestData(subject_id=not_an_iri)


def test_legacy_pac_id_kwarg_still_accepted():
    r = AttributeRequestData(pac_id=dummy_pac)
    assert r.subject_id == dummy_pac


def test_legacy_pac_id_property_still_readable_and_warns():
    r = AttributeRequestData(subject_id=dummy_pac)
    with pytest.deprecated_call():
        assert r.pac_id == dummy_pac


def test_from_http_request_fixes_azure_double_slash_case_insensitively():
    # Azure meddles with double slashes in a path even when url-encoded; from_http_request
    # patches it back. This must work regardless of case - re.sub's 4th positional arg
    # is `count`, not `flags`, so `re.IGNORECASE` passed positionally silently did nothing.
    r = AttributeRequestData.from_http_request(id='https:/pac.mettorius.com/-MD/BAL500/1234', params={}, headers={})
    assert r.subject_id == 'HTTPS://pac.mettorius.com/-MD/BAL500/1234'

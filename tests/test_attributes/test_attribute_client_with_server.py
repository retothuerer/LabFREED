from datetime import datetime

import pytest

from labfreed.pac_attributes.api_data_models.request import AttributeRequestData
from labfreed.pac_attributes.api_data_models.response import (
    AttributeResponsePayload,
    Spec_AttributeGroup,
)
from labfreed.pac_attributes.client.client import (
    AttributeClient,
    AttributeClientInternalError,
    AttributeServerError,
    AuthenticationError,
    local_attribute_request_callback_factory,
)
from labfreed.pac_attributes.facade.attributes import Attribute, Attributes, Reference
from labfreed.pac_attributes.facade.dict_data_source import Dict_DataSource
from labfreed.pac_attributes.server.attribute_data_sources import AttributeGroupDataSource
from labfreed.pac_attributes.server.server import AttributeServerRequestHandler, InvalidRequestError
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource
from labfreed.utilities.translations import Term, Terms

NORMAL_PAC_ID = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340"
CAL_PAC_ID = "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002"
TRAILING_SLASH_PAC_ID = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345/"
GENERIC_IRI = "https://example.com/thing?x=1"
SUBSTANCE_PAC_ID = "HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876"
ALIQUOT_PAC_ID = "HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/+ACMELABS.COM/250:1"


def _build_handler():
    data_source = Dict_DataSource(
        attribute_group_key="ProductionData",
        data={
            NORMAL_PAC_ID: Attributes(
                [
                    Attribute(key="MfgDate", value=datetime(
                        2015, 10, 1, 10, 12)),
                    Attribute(key="CalWeight", value=Reference(CAL_PAC_ID)),
                ]
            ),
            CAL_PAC_ID: Attributes(
                [
                    Attribute(key="NominalWeight", value="50 g"),
                ]
            ),
            TRAILING_SLASH_PAC_ID: Attributes(
                [
                    Attribute(key="MfgDate", value=datetime(2020, 1, 1)),
                ]
            ),
            GENERIC_IRI: Attributes(
                [
                    Attribute(key="MfgDate", value=datetime(2021, 1, 1)),
                ]
            ),
            SUBSTANCE_PAC_ID: Attributes(
                [
                    Attribute(key="MfgDate", value=datetime(2022, 3, 1)),
                ]
            ),
            ALIQUOT_PAC_ID: Attributes(
                [
                    Attribute(key="MfgDate", value=datetime(2023, 5, 1)),
                ]
            ),
        },
    )
    translations = Terms(
        terms=[
            Term.create("MfgDate", [("en", "Manufacturing date")]),
            Term.create("CalWeight", [("en", "Calibration weight")]),
            Term.create("NominalWeight", [("en", "Nominal weight")]),
        ]
    )
    translation_data_source = DictTranslationDataSource(
        data=translations, supported_languages=["en"]
    )
    return AttributeServerRequestHandler(
        data_sources=[data_source],
        translation_data_sources=[translation_data_source],
        default_language="en",
    )


def _build_client():
    handler = _build_handler()
    return AttributeClient(http_post_callback=local_attribute_request_callback_factory(handler))


def _build_handler_data_source_and_translations():
    """Minimal (data_source, translation_data_source) pair for tests that only care
    about AttributeServerRequestHandler's constructor, not the fixture data itself."""
    data_source = Dict_DataSource(
        attribute_group_key="ProductionData",
        data={NORMAL_PAC_ID: Attributes(
            [Attribute(key="MfgDate", value=datetime(2015, 10, 1))])},
    )
    translations = Terms(
        terms=[Term.create("MfgDate", [("en", "Manufacturing date")])])
    translation_data_source = DictTranslationDataSource(
        data=translations, supported_languages=["en"]
    )
    return data_source, translation_data_source


def test_client_gets_attributes_for_a_normal_pac_id():
    client = _build_client()
    groups = client.get_attributes(server_url="", subject_id=NORMAL_PAC_ID)
    assert len(groups) == 1
    assert groups[0].group_key == "ProductionData"
    assert set(groups[0].attributes.keys()) == {"MfgDate", "CalWeight"}


def test_referenced_pac_id_is_forward_looked_up_but_not_returned_directly():
    # CalWeight on NORMAL_PAC_ID is a reference to CAL_PAC_ID - the server does a forward
    # lookup and includes CAL_PAC_ID's own attributes in the response (for the client's
    # cache), but get_attributes() should only return the attribute groups for the id
    # actually requested, not the referenced one.
    client = _build_client()
    groups = client.get_attributes(server_url="", subject_id=NORMAL_PAC_ID)
    assert len(groups) == 1
    assert "NominalWeight" not in groups[0].attributes


def test_client_gets_attributes_for_a_trailing_slash_pac_id():
    # the original bug: a PAC-ID-shaped id with an empty (trailing-slash) segment isn't
    # a strictly valid PAC-ID, but the attribute service only requires it to be an IRI.
    client = _build_client()
    groups = client.get_attributes(
        server_url="", subject_id=TRAILING_SLASH_PAC_ID)
    assert len(groups) == 1
    assert groups[0].attributes["MfgDate"].items[0].value == datetime(
        2020, 1, 1).date()


def test_client_gets_attributes_for_a_generic_non_pac_id_iri():
    client = _build_client()
    groups = client.get_attributes(server_url="", subject_id=GENERIC_IRI)
    assert len(groups) == 1
    assert groups[0].attributes["MfgDate"].items[0].value == datetime(
        2021, 1, 1).date()


def test_old_pac_id_keyword_still_works_and_warns():
    # get_attributes()'s subject_id parameter used to be named pac_id - kept working via
    # a deprecated keyword shim, matching the rest of the IRI migration's naming.
    client = _build_client()
    with pytest.deprecated_call():
        groups = client.get_attributes(server_url="", pac_id=NORMAL_PAC_ID)
    assert len(groups) == 1
    assert groups[0].group_key == "ProductionData"


def test_no_attributes_found_returns_empty_list_not_a_crash():
    client = _build_client()
    groups = client.get_attributes(
        server_url="", subject_id="HTTPS://PAC.METTORIUS.COM/-MD/UNKNOWN/000"
    )
    assert groups == []


def test_derivation_parent_attributes_are_included_under_parents_id():
    # ALIQUOT_PAC_ID was derived from SUBSTANCE_PAC_ID (+ACMELABS.COM marker) - the
    # server should include the parent's own attributes in the response, under the
    # parent's own id, alongside the subject's.
    handler = _build_handler()
    request = AttributeRequestData(subject_id=ALIQUOT_PAC_ID)
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    items_by_id = {item.id: item for item in payload.data}

    assert ALIQUOT_PAC_ID in items_by_id
    assert (
        items_by_id[ALIQUOT_PAC_ID].attribute_groups[0].attributes["MfgDate"].items[0].value
        == datetime(2023, 5, 1).date()
    )

    assert SUBSTANCE_PAC_ID in items_by_id
    assert (
        items_by_id[SUBSTANCE_PAC_ID].attribute_groups[0].attributes["MfgDate"].items[0].value
        == datetime(2022, 3, 1).date()
    )


def test_derivation_lookup_can_be_disabled():
    handler = _build_handler()
    request = AttributeRequestData(
        subject_id=ALIQUOT_PAC_ID, do_derivation_lookup=False)
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    ids = {item.id for item in payload.data}
    assert SUBSTANCE_PAC_ID not in ids


def test_self_derived_parent_attributes_are_included_without_a_marker():
    # NORMAL_PAC_ID ("-MD/BAL500/12340") was derived by its own issuer from the
    # model-level PAC-ID ("-MD/BAL500") by appending a serial number - no
    # +<namespace> marker is needed for this, since there's no third-party
    # attribution to preserve (PAC-ID spec, "Issuing derived PAC-ID"s). Forward
    # lookup is disabled here to isolate this from NORMAL_PAC_ID's unrelated
    # CalWeight reference.
    handler = _build_handler()
    request = AttributeRequestData(
        subject_id=NORMAL_PAC_ID, do_forward_lookup=False)
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    ids = {item.id for item in payload.data}
    assert "HTTPS://PAC.METTORIUS.COM/-MD/BAL500" in ids


def test_single_field_category_has_no_parent_entry():
    # Dropping "BAL500" would leave only the bare category key "-MD", which isn't
    # a meaningful narrower entity to report as a parent.
    handler = _build_handler()
    request = AttributeRequestData(
        subject_id="HTTPS://PAC.METTORIUS.COM/-MD/BAL500")
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    assert len(payload.data) == 1
    assert payload.data[0].id == "HTTPS://PAC.METTORIUS.COM/-MD/BAL500"


def _translations(*keys):
    return DictTranslationDataSource(
        data=Terms(terms=[Term.create(k, [("en", k)]) for k in keys]),
        supported_languages=["en"],
    )


class _FakeRemoteDataSource(AttributeGroupDataSource):
    """Mimics a live remote proxy (e.g. RemoteAttributeDataSource): its
    attribute_group_keys is declared empty since it doesn't know its groups ahead of
    time, so the request handler always queries it and relies on the post-hoc filter
    rather than the pre-filter that other, declared-key sources go through."""

    def __init__(self, groups_by_subject):
        self._groups_by_subject = groups_by_subject
        super().__init__(attribute_group_key=[])

    @property
    def provides_attributes(self):
        return []

    def attributes(self, subject_id):
        return self._groups_by_subject.get(subject_id)


class _RaisingDataSource(AttributeGroupDataSource):
    def __init__(self, group_key):
        super().__init__(attribute_group_key=group_key)

    @property
    def provides_attributes(self):
        return []

    def attributes(self, subject_id):
        raise RuntimeError("boom")


def test_constructor_accepts_a_single_data_source_not_wrapped_in_a_list():
    data_source, tds = _build_handler_data_source_and_translations()
    handler = AttributeServerRequestHandler(
        data_sources=data_source,
        translation_data_sources=[tds],
        default_language="en",
    )
    assert handler._attribute_group_data_sources == [data_source]


def test_constructor_raises_when_no_translation_data_source_supports_any_language():
    data_source, _ = _build_handler_data_source_and_translations()
    with pytest.raises(ValueError):
        AttributeServerRequestHandler(
            data_sources=[data_source],
            translation_data_sources=[],
            default_language="en",
        )


def test_constructor_raises_when_default_language_is_not_supported():
    data_source, tds = _build_handler_data_source_and_translations()
    with pytest.raises(ValueError):
        AttributeServerRequestHandler(
            data_sources=[data_source],
            translation_data_sources=[tds],
            default_language="fr",
        )


def test_handle_attribute_request_raises_on_non_request_data_argument():
    handler = _build_handler()
    with pytest.raises(ValueError):
        handler.handle_attribute_request("not a request")


def test_handle_attribute_request_wraps_validation_failure_in_invalid_request_error():
    handler = _build_handler()
    # bypasses AttributeRequestData's own validators, so re-validation inside
    # handle_attribute_request is what actually catches the invalid subject_id.
    bad_request = AttributeRequestData.model_construct(subject_id="not a url")
    with pytest.raises(InvalidRequestError):
        handler.handle_attribute_request(bad_request)


def test_restrict_to_attribute_groups_filters_out_other_declared_sources_and_keeps_undeclared_ones():
    # "RemoteData" is only provided by the undeclared-keys fake source; "ProductionData"
    # comes from a normal, declared-key source that should be pre-filtered out entirely.
    production = Dict_DataSource(
        attribute_group_key="ProductionData",
        data={NORMAL_PAC_ID: Attributes(
            [Attribute(key="MfgDate", value=datetime(2015, 10, 1))])},
    )
    remote = _FakeRemoteDataSource(
        {
            NORMAL_PAC_ID: Spec_AttributeGroup(
                group_key="RemoteData",
                attributes=Attributes(
                    [Attribute(key="RemoteKey", value="v")]
                ).to_payload_attributes(),
            )
        }
    )
    handler = AttributeServerRequestHandler(
        data_sources=[production, remote],
        translation_data_sources=[_translations("MfgDate", "RemoteKey")],
        default_language="en",
    )
    request = AttributeRequestData(
        subject_id=NORMAL_PAC_ID, restrict_to_attribute_groups=["RemoteData"]
    )
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    group_keys = {
        g.group_key for item in payload.data for g in item.attribute_groups}
    assert group_keys == {"RemoteData"}


def test_exception_from_a_data_source_propagates_out_of_handle_attribute_request():
    handler = AttributeServerRequestHandler(
        data_sources=[_RaisingDataSource("Boom")],
        translation_data_sources=[_translations()],
        default_language="en",
    )
    request = AttributeRequestData(subject_id=NORMAL_PAC_ID)
    with pytest.raises(RuntimeError):
        handler.handle_attribute_request(request)


def test_keep_duplicate_attributes_all_keeps_both_sources_values():
    ds_a = Dict_DataSource(
        attribute_group_key="A",
        data={NORMAL_PAC_ID: Attributes([Attribute(key="Shared", value="from_a")])},
    )
    ds_b = Dict_DataSource(
        attribute_group_key="B",
        data={NORMAL_PAC_ID: Attributes([Attribute(key="Shared", value="from_b")])},
    )
    handler = AttributeServerRequestHandler(
        data_sources=[ds_a, ds_b],
        translation_data_sources=[_translations("Shared")],
        default_language="en",
        keep_duplicate_attributes="all",
    )
    request = AttributeRequestData(subject_id=NORMAL_PAC_ID)
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    groups_with_shared = {
        g.group_key
        for item in payload.data
        for g in item.attribute_groups
        if "Shared" in g.attributes
    }
    assert groups_with_shared == {"A", "B"}


def test_keep_duplicate_attributes_last_keeps_the_later_sources_value():
    ds_a = Dict_DataSource(
        attribute_group_key="A",
        data={NORMAL_PAC_ID: Attributes(
            [Attribute(key="Shared", value="from_a")])},
    )
    ds_b = Dict_DataSource(
        attribute_group_key="B",
        data={NORMAL_PAC_ID: Attributes(
            [Attribute(key="Shared", value="from_b")])},
    )
    handler = AttributeServerRequestHandler(
        data_sources=[ds_a, ds_b],
        translation_data_sources=[_translations("Shared")],
        default_language="en",
        keep_duplicate_attributes="last",
    )
    request = AttributeRequestData(subject_id=NORMAL_PAC_ID)
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    groups_with_shared = [
        g.group_key
        for item in payload.data
        for g in item.attribute_groups
        if "Shared" in g.attributes
    ]
    assert groups_with_shared == ["B"]


def test_keep_duplicate_attributes_first_keeps_the_earlier_sources_value():
    ds_a = Dict_DataSource(
        attribute_group_key="A",
        data={NORMAL_PAC_ID: Attributes(
            [Attribute(key="Shared", value="from_a")])},
    )
    ds_b = Dict_DataSource(
        attribute_group_key="B",
        data={NORMAL_PAC_ID: Attributes(
            [Attribute(key="Shared", value="from_b")])},
    )
    handler = AttributeServerRequestHandler(
        data_sources=[ds_a, ds_b],
        translation_data_sources=[_translations("Shared")],
        default_language="en",
        keep_duplicate_attributes="first",
    )
    request = AttributeRequestData(subject_id=NORMAL_PAC_ID)
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    groups_with_shared = [
        g.group_key
        for item in payload.data
        for g in item.attribute_groups
        if "Shared" in g.attributes
    ]
    assert groups_with_shared == ["A"]


def test_keep_duplicate_attributes_invalid_value_warns_and_keeps_everything():
    ds_a = Dict_DataSource(
        attribute_group_key="A",
        data={NORMAL_PAC_ID: Attributes(
            [Attribute(key="Shared", value="from_a")])},
    )
    ds_b = Dict_DataSource(
        attribute_group_key="B",
        data={NORMAL_PAC_ID: Attributes(
            [Attribute(key="Shared", value="from_b")])},
    )
    handler = AttributeServerRequestHandler(
        data_sources=[ds_a, ds_b],
        translation_data_sources=[_translations("Shared")],
        default_language="en",
        keep_duplicate_attributes="bogus",
    )
    request = AttributeRequestData(subject_id=NORMAL_PAC_ID)
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    groups_with_shared = {
        g.group_key
        for item in payload.data
        for g in item.attribute_groups
        if "Shared" in g.attributes
    }
    assert groups_with_shared == {"A", "B"}


def test_malformed_reference_value_is_not_followed_and_does_not_crash():
    ds = Dict_DataSource(
        attribute_group_key="ProductionData",
        data={
            NORMAL_PAC_ID: Attributes(
                [Attribute(key="BadRef", value=Reference("not-a-real-pac-id"))]
            )
        },
    )
    handler = AttributeServerRequestHandler(
        data_sources=[ds],
        translation_data_sources=[_translations("BadRef")],
        default_language="en",
    )
    request = AttributeRequestData(subject_id=NORMAL_PAC_ID)
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    ids = {item.id for item in payload.data}
    assert "not-a-real-pac-id" not in ids


def test_attribute_group_label_uses_translation_when_the_group_key_itself_has_one():
    # every other fixture in this file omits a translation for the group's own key,
    # so it always takes the fallback branch (fallback_label) instead of this one.
    ds = Dict_DataSource(
        attribute_group_key="ProductionData",
        data={NORMAL_PAC_ID: Attributes(
            [Attribute(key="MfgDate", value=datetime(2015, 10, 1))])},
    )
    handler = AttributeServerRequestHandler(
        data_sources=[ds],
        translation_data_sources=[_translations("MfgDate", "ProductionData")],
        default_language="en",
    )
    request = AttributeRequestData(subject_id=NORMAL_PAC_ID)
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    assert payload.data[0].attribute_groups[0].group_label == "ProductionData"


def test_response_language_follows_requested_language_preferences():
    handler = _build_handler()
    request = AttributeRequestData(
        subject_id=NORMAL_PAC_ID, language_preferences=["en"])
    payload = AttributeResponsePayload.model_validate_json(
        handler.handle_attribute_request(request)
    )
    assert payload.language == "en"


def test_get_attributes_rejects_unexpected_keyword_arguments():
    client = _build_client()
    with pytest.raises(TypeError):
        client.get_attributes(server_url="", subject_id=NORMAL_PAC_ID, foo=1)


def test_get_attributes_requires_subject_id():
    client = _build_client()
    with pytest.raises(TypeError):
        client.get_attributes(server_url="")


def test_get_attributes_raises_internal_error_on_400():
    client = AttributeClient(
        http_post_callback=lambda url, req: (400, "bad request"))
    with pytest.raises(AttributeClientInternalError):
        client.get_attributes(server_url="", subject_id=NORMAL_PAC_ID)


def test_get_attributes_raises_authentication_error_on_401():
    client = AttributeClient(
        http_post_callback=lambda url, req: (401, "unauthorized"))
    with pytest.raises(AuthenticationError):
        client.get_attributes(server_url="", subject_id=NORMAL_PAC_ID)


def test_get_attributes_returns_empty_list_on_404():
    client = AttributeClient(
        http_post_callback=lambda url, req: (404, "not found"))
    assert client.get_attributes(server_url="", subject_id=NORMAL_PAC_ID) == []


def test_get_attributes_raises_server_error_on_500():
    client = AttributeClient(
        http_post_callback=lambda url, req: (500, "internal error"))
    with pytest.raises(AttributeServerError):
        client.get_attributes(server_url="", subject_id=NORMAL_PAC_ID)


def test_get_attributes_raises_server_error_on_a_response_that_fails_validation():
    client = AttributeClient(
        http_post_callback=lambda url, req: (
            200, "not valid json for the payload model")
    )
    with pytest.raises(AttributeServerError):
        client.get_attributes(server_url="", subject_id=NORMAL_PAC_ID)

from datetime import datetime

from labfreed.pac_attributes.api_data_models.request import AttributeRequestData
from labfreed.pac_attributes.api_data_models.response import AttributeResponsePayload
from labfreed.pac_attributes.client.client import AttributeClient
from labfreed.pac_attributes.facade.attributes import Attribute, Attributes, Reference
from labfreed.pac_attributes.facade.dict_data_source import Dict_DataSource
from labfreed.pac_attributes.server.server import AttributeServerRequestHandler
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
            NORMAL_PAC_ID: Attributes([
                Attribute(key="MfgDate", value=datetime(2015, 10, 1, 10, 12)),
                Attribute(key="CalWeight", value=Reference(CAL_PAC_ID)),
            ]),
            CAL_PAC_ID: Attributes([
                Attribute(key="NominalWeight", value="50 g"),
            ]),
            TRAILING_SLASH_PAC_ID: Attributes([
                Attribute(key="MfgDate", value=datetime(2020, 1, 1)),
            ]),
            GENERIC_IRI: Attributes([
                Attribute(key="MfgDate", value=datetime(2021, 1, 1)),
            ]),
            SUBSTANCE_PAC_ID: Attributes([
                Attribute(key="MfgDate", value=datetime(2022, 3, 1)),
            ]),
            ALIQUOT_PAC_ID: Attributes([
                Attribute(key="MfgDate", value=datetime(2023, 5, 1)),
            ]),
        },
    )
    translations = Terms(terms=[
        Term.create("MfgDate", [("en", "Manufacturing date")]),
        Term.create("CalWeight", [("en", "Calibration weight")]),
        Term.create("NominalWeight", [("en", "Nominal weight")]),
    ])
    translation_data_source = DictTranslationDataSource(data=translations, supported_languages=["en"])
    return AttributeServerRequestHandler(
        data_sources=[data_source],
        translation_data_sources=[translation_data_source],
        default_language="en",
    )


def _build_client():
    handler = _build_handler()

    def local_callback(url, attribute_request_data):
        try:
            return 200, handler.handle_attribute_request(attribute_request_data)
        except Exception as e:
            return 500, str(e)

    return AttributeClient(http_post_callback=local_callback)


def test_client_gets_attributes_for_a_normal_pac_id():
    client = _build_client()
    groups = client.get_attributes(server_url="", pac_id=NORMAL_PAC_ID)
    assert len(groups) == 1
    assert groups[0].group_key == "ProductionData"
    assert set(groups[0].attributes.keys()) == {"MfgDate", "CalWeight"}


def test_referenced_pac_id_is_forward_looked_up_but_not_returned_directly():
    # CalWeight on NORMAL_PAC_ID is a reference to CAL_PAC_ID - the server does a forward
    # lookup and includes CAL_PAC_ID's own attributes in the response (for the client's
    # cache), but get_attributes() should only return the attribute groups for the id
    # actually requested, not the referenced one.
    client = _build_client()
    groups = client.get_attributes(server_url="", pac_id=NORMAL_PAC_ID)
    assert len(groups) == 1
    assert "NominalWeight" not in groups[0].attributes


def test_client_gets_attributes_for_a_trailing_slash_pac_id():
    # the original bug: a PAC-ID-shaped id with an empty (trailing-slash) segment isn't
    # a strictly valid PAC-ID, but the attribute service only requires it to be an IRI.
    client = _build_client()
    groups = client.get_attributes(server_url="", pac_id=TRAILING_SLASH_PAC_ID)
    assert len(groups) == 1
    assert groups[0].attributes["MfgDate"].items[0].value == datetime(2020, 1, 1).date()


def test_client_gets_attributes_for_a_generic_non_pac_id_iri():
    client = _build_client()
    groups = client.get_attributes(server_url="", pac_id=GENERIC_IRI)
    assert len(groups) == 1
    assert groups[0].attributes["MfgDate"].items[0].value == datetime(2021, 1, 1).date()


def test_no_attributes_found_returns_empty_list_not_a_crash():
    client = _build_client()
    groups = client.get_attributes(server_url="", pac_id="HTTPS://PAC.METTORIUS.COM/-MD/UNKNOWN/000")
    assert groups == []


def test_derivation_parent_attributes_are_included_under_parents_id():
    # ALIQUOT_PAC_ID was derived from SUBSTANCE_PAC_ID (+ACMELABS.COM marker) - the
    # server should include the parent's own attributes in the response, under the
    # parent's own id, alongside the subject's.
    handler = _build_handler()
    request = AttributeRequestData(subject_id=ALIQUOT_PAC_ID)
    payload = AttributeResponsePayload.model_validate_json(handler.handle_attribute_request(request))
    items_by_id = {item.id: item for item in payload.data}

    assert ALIQUOT_PAC_ID in items_by_id
    assert items_by_id[ALIQUOT_PAC_ID].attribute_groups[0].attributes["MfgDate"].items[0].value == datetime(2023, 5, 1).date()

    assert SUBSTANCE_PAC_ID in items_by_id
    assert items_by_id[SUBSTANCE_PAC_ID].attribute_groups[0].attributes["MfgDate"].items[0].value == datetime(2022, 3, 1).date()


def test_derivation_lookup_can_be_disabled():
    handler = _build_handler()
    request = AttributeRequestData(subject_id=ALIQUOT_PAC_ID, do_derivation_lookup=False)
    payload = AttributeResponsePayload.model_validate_json(handler.handle_attribute_request(request))
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
    request = AttributeRequestData(subject_id=NORMAL_PAC_ID, do_forward_lookup=False)
    payload = AttributeResponsePayload.model_validate_json(handler.handle_attribute_request(request))
    ids = {item.id for item in payload.data}
    assert "HTTPS://PAC.METTORIUS.COM/-MD/BAL500" in ids


def test_single_field_category_has_no_parent_entry():
    # Dropping "BAL500" would leave only the bare category key "-MD", which isn't
    # a meaningful narrower entity to report as a parent.
    handler = _build_handler()
    request = AttributeRequestData(subject_id="HTTPS://PAC.METTORIUS.COM/-MD/BAL500")
    payload = AttributeResponsePayload.model_validate_json(handler.handle_attribute_request(request))
    assert len(payload.data) == 1
    assert payload.data[0].id == "HTTPS://PAC.METTORIUS.COM/-MD/BAL500"

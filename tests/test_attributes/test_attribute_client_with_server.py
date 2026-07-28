from datetime import datetime

from labfreed.pac_attributes.client.client import AttributeClient
from labfreed.pac_attributes.pythonic.py_attributes import pyAttribute, pyAttributes, pyReference
from labfreed.pac_attributes.pythonic.py_dict_data_source import pyDict_DataSource
from labfreed.pac_attributes.server.server import AttributeServerRequestHandler
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource
from labfreed.utilities.translations import Term, Terms

NORMAL_PAC_ID = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340"
CAL_PAC_ID = "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002"
TRAILING_SLASH_PAC_ID = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345/"
GENERIC_IRI = "https://example.com/thing?x=1"


def _build_client():
    data_source = pyDict_DataSource(
        attribute_group_key="ProductionData",
        data={
            NORMAL_PAC_ID: pyAttributes([
                pyAttribute(key="MfgDate", value=datetime(2015, 10, 1, 10, 12)),
                pyAttribute(key="CalWeight", value=pyReference(CAL_PAC_ID)),
            ]),
            CAL_PAC_ID: pyAttributes([
                pyAttribute(key="NominalWeight", value="50 g"),
            ]),
            TRAILING_SLASH_PAC_ID: pyAttributes([
                pyAttribute(key="MfgDate", value=datetime(2020, 1, 1)),
            ]),
            GENERIC_IRI: pyAttributes([
                pyAttribute(key="MfgDate", value=datetime(2021, 1, 1)),
            ]),
        },
    )
    translations = Terms(terms=[
        Term.create("MfgDate", [("en", "Manufacturing date")]),
        Term.create("CalWeight", [("en", "Calibration weight")]),
        Term.create("NominalWeight", [("en", "Nominal weight")]),
    ])
    translation_data_source = DictTranslationDataSource(data=translations, supported_languages=["en"])
    handler = AttributeServerRequestHandler(
        data_sources=[data_source],
        translation_data_sources=[translation_data_source],
        default_language="en",
    )

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

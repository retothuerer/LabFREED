from datetime import datetime
from urllib.parse import quote

from labfreed.labfreed_extended.pac_issuer_lib.lib.attribute_server_factory import (
    AttributeServerFactory,
    NoAuthRequiredAuthenticator,
    Webframework,
)
from labfreed.pac_attributes.facade.py_attributes import Attribute, Attributes
from labfreed.pac_attributes.facade.py_dict_data_source import pyDict_DataSource
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource
from labfreed.utilities.translations import Term, Terms

NORMAL_PAC_ID = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340"
TRAILING_SLASH_PAC_ID = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345/"


def _build_test_client():
    data_source = pyDict_DataSource(
        attribute_group_key="ProductionData",
        data={
            NORMAL_PAC_ID: Attributes([Attribute(key="MfgDate", value=datetime(2015, 10, 1))]),
            TRAILING_SLASH_PAC_ID: Attributes([Attribute(key="MfgDate", value=datetime(2020, 1, 1))]),
        },
    )
    translations = Terms(terms=[Term.create("MfgDate", [("en", "Manufacturing date")])])
    translation_data_source = DictTranslationDataSource(data=translations, supported_languages=["en"])

    app = AttributeServerFactory.create_server_app(
        datasources=[data_source],
        default_language="en",
        translation_data_sources=[translation_data_source],
        authenticator=NoAuthRequiredAuthenticator(),
        framework=Webframework.FLASK,
    )
    return app.test_client()


def test_capabilities_page_is_reachable():
    client = _build_test_client()
    resp = client.get("/")
    assert resp.status_code == 200


def test_get_attributes_for_a_normal_pac_id_over_http():
    client = _build_test_client()
    resp = client.get(f"/{quote(NORMAL_PAC_ID, safe='')}")
    assert resp.status_code == 200
    assert "MfgDate" in resp.get_data(as_text=True)


def test_get_attributes_for_a_trailing_slash_pac_id_over_http():
    # the original bug, exercised through the real HTTP path (URL-encoded id in the
    # request path, not just the Python API) - this used to 500 instead of 200.
    client = _build_test_client()
    resp = client.get(f"/{quote(TRAILING_SLASH_PAC_ID, safe='')}")
    assert resp.status_code == 200
    assert "MfgDate" in resp.get_data(as_text=True)

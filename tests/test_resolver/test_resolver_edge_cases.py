import pytest

from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id_resolver import resolver
from labfreed.pac_id_resolver.resolver import PAC_ID_Resolver, cit_from_str
from labfreed.pac_id_resolver.resolver_config import ResolverConfig

_YML_NO_ORIGIN = '''
config:
  - if: True
    entries:
      - service_name: Location
        application_intents: [update-location]
        service_type: action-generic
        template_url: "https://example.com/actions/update_location?location={$.client_info.location}"
'''

_YML_WITH_ORIGIN_TEMPLATE = '''
origin: {issuer}
config:
  - if: True
    entries:
      - service_name: IssuerService
        application_intents: [issuer-lookup]
        service_type: action-generic
        template_url: "https://example.com/issuer"
'''


class _RaisingResolverConfig:
    """A resolver-config double whose evaluate_pac_id() always raises, to confirm
    resolve() logs and skips a broken config rather than letting it blow up the whole
    resolve() call for every other, working config."""
    origin = "raising"

    def evaluate_pac_id(self, pac_id, client_info=None):
        raise RuntimeError("boom")


def test_cit_from_str_logs_validation_messages_when_the_loaded_config_has_any():
    # every existing fixture sets `origin`, so cit.validation_messages() is always
    # empty and _log_cit_validation_messages' loop body never runs. Omitting origin
    # (defaults to '') triggers ResolverConfig's own "Origin should not be empty"
    # WARNING, giving the loop something to actually log.
    cit = cit_from_str(_YML_NO_ORIGIN)
    assert isinstance(cit, ResolverConfig)
    assert len(cit.validation_messages()) >= 1


def test_resolve_raises_when_pac_id_is_neither_a_string_nor_a_pac_id():
    r = PAC_ID_Resolver()
    with pytest.raises(ValueError):
        r.resolve(12345)


def test_resolver_configs_default_to_empty_and_can_be_added_and_removed():
    r = PAC_ID_Resolver()
    assert r._resolver_configs == set()

    rc = ResolverConfig.from_yaml(_YML_NO_ORIGIN)
    r.add_resolver_config(rc)
    assert rc in r._resolver_configs

    r.remove_resolver_config(rc)
    assert rc not in r._resolver_configs


def test_resolve_skips_a_resolver_config_that_raises_instead_of_propagating():
    pac = PAC_CAT.from_url('HTTPS://PAC.METTORIUS.COM/-MS/X3511/CAS:7732-18-5')
    r = PAC_ID_Resolver(resolver_configs=[_RaisingResolverConfig()])
    result = r.resolve(pac, check_service_status=False, use_issuer_resolver_config=False)
    assert result == []


def test_get_issuer_resolver_config_fetches_and_parses_the_v2_resolver_config(monkeypatch):
    issuer = "TESTISSUER123.COM"
    yml = _YML_WITH_ORIGIN_TEMPLATE.format(issuer=issuer)

    def fake_get(url, timeout=2):
        if "resolver_config.yaml" in url:
            return type("Resp", (), {"status_code": 200, "text": yml})()
        return type("Resp", (), {"status_code": 404, "text": ""})()

    monkeypatch.setattr(resolver, "get", fake_get)
    resolver._get_issuer_resolver_config.cache_clear()

    rc = resolver._get_issuer_resolver_config(issuer)

    assert isinstance(rc, ResolverConfig)
    assert rc.origin == issuer


def test_resolve_includes_services_from_the_issuers_own_resolver_config(monkeypatch):
    issuer = "TESTISSUER456.COM"
    yml = _YML_WITH_ORIGIN_TEMPLATE.format(issuer=issuer)

    def fake_get(url, timeout=2):
        if "resolver_config.yaml" in url:
            return type("Resp", (), {"status_code": 200, "text": yml})()
        return type("Resp", (), {"status_code": 404, "text": ""})()

    monkeypatch.setattr(resolver, "get", fake_get)
    resolver._get_issuer_resolver_config.cache_clear()

    pac = PAC_CAT.from_url(f'HTTPS://PAC.{issuer}/-MS/X3511/CAS:7732-18-5')
    result = PAC_ID_Resolver().resolve(pac, check_service_status=False, use_issuer_resolver_config=True)

    urls = [s.url for sg in result for s in sg.services]
    assert any("example.com/issuer" in u for u in urls)

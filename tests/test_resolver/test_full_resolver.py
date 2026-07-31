from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id_resolver.resolver import PAC_ID_Resolver
from labfreed.pac_id_resolver.resolver_config import ResolverConfig

_YML = '''
origin: test
config:
  - if: True
    entries:
      - service_name: Location
        application_intents: [update-location]
        service_type: action-generic
        template_url: "https://example.com/actions/update_location?location={$.client_info.location}"
'''
_PAC = PAC_CAT.from_url('HTTPS://PAC.METTORIUS.COM/-MS/X3511/CAS:7732-18-5')


def _urls(result):
    return [s.url for sg in result for s in sg.services]


def test_resolve_forwards_client_info_to_resolver_config_template():
    '''PAC_ID_Resolver.resolve()'s client_info kwarg reaches ResolverConfig.evaluate_pac_id()
    unchanged - see test_resolver_config_v2.py for the actual merge-into-Resolver-Context
    behavior, this only covers the pass-through wiring.'''
    rc = ResolverConfig.from_yaml(_YML)

    result = PAC_ID_Resolver(resolver_configs=[rc]).resolve(
        _PAC, check_service_status=False, use_issuer_resolver_config=False,
        client_info={'location': 'HTTPS://PAC.BUCHI.COM/-MD/C-950/FAKE0000'},
    )

    assert any('HTTPS%3A//PAC.BUCHI.COM' in u for u in _urls(result))


def test_resolve_falls_back_to_the_resolver_s_own_client_info_default():
    rc = ResolverConfig.from_yaml(_YML)
    resolver = PAC_ID_Resolver(
        resolver_configs=[rc],
        client_info={'location': 'HTTPS://PAC.BUCHI.COM/-MD/C-950/FAKE0000'},
    )

    result = resolver.resolve(_PAC, check_service_status=False, use_issuer_resolver_config=False)

    assert any('HTTPS%3A//PAC.BUCHI.COM' in u for u in _urls(result))


def test_resolve_s_client_info_overrides_the_resolver_s_own_default():
    rc = ResolverConfig.from_yaml(_YML)
    resolver = PAC_ID_Resolver(
        resolver_configs=[rc],
        client_info={'location': 'HTTPS://PAC.BUCHI.COM/-MD/C-950/FAKE0000'},
    )

    result = resolver.resolve(
        _PAC, check_service_status=False, use_issuer_resolver_config=False,
        client_info={'location': 'HTTPS://PAC.GIVAUDAN.COM/-X/LAB1'},
    )

    urls = _urls(result)
    assert any('PAC.GIVAUDAN.COM' in u for u in urls)
    assert not any('PAC.BUCHI.COM' in u for u in urls)

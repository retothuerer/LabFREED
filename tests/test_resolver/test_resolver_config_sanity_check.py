'''
Sanity checks against real resolver configs -- as opposed to the small, hand
crafted snippets in test_resolver_config_v2.py, these load whole config files
that are either shipped as examples or actually used in the labfreed-webtools
resolver tester, and resolve real PAC-IDs against them.
'''
import os
import pytest

from labfreed.pac_id_resolver.resolver_config import ResolverConfig
from labfreed.pac_cat.pac_cat import PAC_CAT

HERE = os.path.dirname(__file__)

# Sample PAC-IDs used by the live labfreed-webtools resolver tester
# (resolver_tester/bp_resolver_tester.py), plus one with an explicit CAS
# segment (matching tests/test_sanity_check.py::test_resolver) to exercise the
# CAS-search blocks that none of the webtools defaults happen to trigger.
PAC_SUBSTANCE = 'HTTPS://PAC.METTORIUS.COM/-MS/BAL-CLEAN/X45AHDF45'
PAC_DEVICE = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345'
PAC_DERIVED_DEVICE = 'HTTPS://PAC.METTORIUS.COM/-DR/F812EB/-MD/BAL500/12345'
PAC_CONSUMABLE = 'HTTPS://PAC.METTORIUS.COM/-MC/REAGENT-X/LOT:ABC123'
PAC_SUBSTANCE_WITH_CAS = 'HTTPS://PAC.METTORIUS.COM/-MS/BAL-CLEAN/CAS:7732-18-5'


def _load(path):
    with open(path) as f:
        return ResolverConfig.from_yaml(f.read())


def _service_names(rc, pac_url):
    pac = PAC_CAT.from_url(pac_url)
    return [s.service_name for s in rc.evaluate_pac_id(pac).services]


# ---------------------------------------------------------------------------
# cit.yaml (local fixture)
# ---------------------------------------------------------------------------

def test_cit_yaml_is_valid():
    rc = _load(os.path.join(HERE, 'cit.yaml'))
    assert rc.is_valid


def test_cit_yaml_device_gets_shop_and_manual_and_logic_showcase_entries():
    # the unconditional "Test" block and the "-MD"-gated "Instruments" block
    # both match a device PAC-ID, so Shop/Manual legitimately appear twice --
    # plus the three logic-showcase entries that also require "-MD", plus the
    # always-applicable "not not equal issuer" entry.
    rc = _load(os.path.join(HERE, 'cit.yaml'))
    assert sorted(_service_names(rc, PAC_DEVICE)) == sorted([
        'Shop', 'Manual', 'Shop', 'Manual',
        'multiline if', 'folded if', 'double not if', 'not not equal issuer',
    ])


def test_cit_yaml_consumable_also_gets_coa():
    rc = _load(os.path.join(HERE, 'cit.yaml'))
    assert sorted(_service_names(rc, PAC_CONSUMABLE)) == sorted([
        'Shop', 'Manual', 'Shop', 'Manual', 'CoA', 'not not equal issuer',
    ])


# ---------------------------------------------------------------------------
# v2_basic.yaml (copied from labfreed-webtools resolver_tester/static/cit_examples)
# ---------------------------------------------------------------------------

def test_v2_basic_is_valid():
    rc = _load(os.path.join(HERE, 'v2_basic.yaml'))
    assert rc.is_valid


def test_v2_basic_device_gets_technical_datasheet_and_shop():
    rc = _load(os.path.join(HERE, 'v2_basic.yaml'))
    assert set(_service_names(rc, PAC_DEVICE)) == {'Technical Datasheet', 'Shop'}


def test_v2_basic_substance_gets_coa_msds_shop():
    rc = _load(os.path.join(HERE, 'v2_basic.yaml'))
    assert set(_service_names(rc, PAC_SUBSTANCE)) == {'CoA', 'MSDS', 'Shop'}


def test_v2_basic_substance_with_cas_also_gets_cas_and_web_search():
    rc = _load(os.path.join(HERE, 'v2_basic.yaml'))
    names = set(_service_names(rc, PAC_SUBSTANCE_WITH_CAS))
    assert {'CoA', 'MSDS', 'Shop', 'CAS Search', 'Web Search'} == names


def test_v2_basic_consumable_gets_nothing():
    # neither block's condition covers "-MC" -- this config simply has no
    # rule for consumables today.
    rc = _load(os.path.join(HERE, 'v2_basic.yaml'))
    assert _service_names(rc, PAC_CONSUMABLE) == []


# ---------------------------------------------------------------------------
# v2_complex.yaml (copied from labfreed-webtools resolver_tester/static/cit_examples)
# ---------------------------------------------------------------------------

def test_v2_complex_is_valid():
    rc = _load(os.path.join(HERE, 'v2_complex.yaml'))
    assert rc.is_valid


def test_v2_complex_substance_gets_chem_inventory_and_google_search():
    rc = _load(os.path.join(HERE, 'v2_complex.yaml'))
    assert set(_service_names(rc, PAC_SUBSTANCE)) == {'Chem Inventory', 'Google Search'}


def test_v2_complex_device_still_gets_chem_inventory_via_or():
    # applicable_if ORs "-MS" and "-MD" together, so a device (no "-MS"
    # category at all) still matches through the "-MD" side.
    rc = _load(os.path.join(HERE, 'v2_complex.yaml'))
    assert set(_service_names(rc, PAC_DEVICE)) == {'Chem Inventory', 'Google Search'}


def test_v2_complex_consumable_only_gets_google_search():
    # "-MC" matches neither side of the "-MS" OR "-MD" condition.
    rc = _load(os.path.join(HERE, 'v2_complex.yaml'))
    assert _service_names(rc, PAC_CONSUMABLE) == ['Google Search']


# ---------------------------------------------------------------------------
# v2_macros.yaml (copied from labfreed-webtools resolver_tester/static/cit_examples)
# ---------------------------------------------------------------------------

def test_v2_macros_is_valid():
    rc = _load(os.path.join(HERE, 'v2_macros.yaml'))
    assert rc.is_valid


def test_v2_macros_device_gets_shop_via_macro():
    # same single-quote bracket shorthand issue as cit.yaml:
    # $.categories['-MD'] never matches, so the macro-based Shop entry never
    # appears for any device PAC-ID today.
    rc = _load(os.path.join(HERE, 'v2_macros.yaml'))
    assert 'Shop' in _service_names(rc, PAC_DEVICE)


def test_v2_macros_substance_with_cas_gets_cas_search():
    rc = _load(os.path.join(HERE, 'v2_macros.yaml'))
    assert 'CAS Search' in _service_names(rc, PAC_SUBSTANCE_WITH_CAS)


def test_v2_macros_always_includes_google_search():
    rc = _load(os.path.join(HERE, 'v2_macros.yaml'))
    for pac_url in (PAC_SUBSTANCE, PAC_DEVICE, PAC_DERIVED_DEVICE, PAC_CONSUMABLE):
        assert 'Google Search' in _service_names(rc, pac_url)


# ---------------------------------------------------------------------------
# cit_mine.yaml (copied from examples/cit_mine.yaml)
# ---------------------------------------------------------------------------

def test_examples_cit_mine_is_valid():
    rc = _load(os.path.join(HERE, 'cit_mine.yaml'))
    assert rc.is_valid


def test_examples_cit_mine_substance_with_cas_gets_cas_search():
    rc = _load(os.path.join(HERE, 'cit_mine.yaml'))
    assert _service_names(rc, PAC_SUBSTANCE_WITH_CAS) == ['CAS Search']


def test_examples_cit_mine_substance_without_cas_gets_nothing():
    rc = _load(os.path.join(HERE, 'cit_mine.yaml'))
    assert _service_names(rc, PAC_SUBSTANCE) == []


# ---------------------------------------------------------------------------
# resolver_config_demo.yaml (copied from examples/resolver_config_demo.yaml)
# ---------------------------------------------------------------------------

def test_examples_resolver_config_demo_is_valid():
    rc = _load(os.path.join(HERE, 'resolver_config_demo.yaml'))
    assert rc.is_valid


def test_examples_resolver_config_demo_device_gets_demo_attributes():
    rc = _load(os.path.join(HERE, 'resolver_config_demo.yaml'))
    assert _service_names(rc, PAC_DEVICE) == ['DemoAttributes']


def test_examples_resolver_config_demo_substance_gets_inventory():
    rc = _load(os.path.join(HERE, 'resolver_config_demo.yaml'))
    assert _service_names(rc, PAC_SUBSTANCE) == ['Inventory']


def test_examples_resolver_config_demo_substance_with_cas_gets_search_services_too():
    rc = _load(os.path.join(HERE, 'resolver_config_demo.yaml'))
    names = set(_service_names(rc, PAC_SUBSTANCE_WITH_CAS))
    assert {'Inventory', 'CAS Search', 'Supplier Search Google'} == names


def test_examples_resolver_config_demo_consumable_gets_nothing():
    rc = _load(os.path.join(HERE, 'resolver_config_demo.yaml'))
    assert _service_names(rc, PAC_CONSUMABLE) == []

'''
Tests for CategorySegment.issuer/.issuing_system - convenience accessors answering
"who added this segment" and "what system was used for that specific derivation",
built on top of derivation_namespace (see test_PAC_CAT_derivation_namespace.py).

Per developer-docs/design-choices.md ("PAC-CAT segment/category context (issuer,
issuing system) must be re-derived on every `.segments` access, not cached on the
segment instance"), neither property is denormalized onto a segment instance once -
both, like derivation_namespace itself, are Python-only and excluded from
serialization.
'''
import pytest

from labfreed.pac_cat import PAC_CAT


valid_base = "HTTPS://PAC.METTORIUS.COM/"


def from_url(url):
    return PAC_CAT.from_url(url, suppress_validation_errors=True)


# ---------------------------------------------------------------------------
# .issuer
# ---------------------------------------------------------------------------

def test_segment_issuer_is_the_pac_ids_own_issuer_when_not_derived():
    pac = from_url(valid_base + "-MD/240:BAL500/21:12345")
    seg = pac.main_category.segments[0]
    assert seg.issuer == 'METTORIUS.COM'


def test_segment_issuer_is_the_derivation_namespace_when_derived():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    ms = pac.get_category('-MS')
    derived_seg = ms.segments[-1]
    assert derived_seg.value == '1'
    assert derived_seg.issuer == 'ACMELABS.COM'


def test_segment_issuer_not_included_in_serialization():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    d = pac.to_dict()
    seg_dicts = d['categories'][0]['segments']
    assert all('issuer' not in s for s in seg_dicts)


def test_segment_derivation_namespace_not_included_in_serialization():
    ''' derivation_namespace itself moved off the wire (see spec_versions.yaml's
    PAC-ID-Resolver entry and design-choices.md) - the resolver spec no longer
    documents it, and exposing it was judged not worth the wire-format cost. '''
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    d = pac.to_dict()
    seg_dicts = d['categories'][0]['segments']
    assert all('derivation_namespace' not in s for s in seg_dicts)
    # still accessible from Python, just not serialized
    assert pac.get_category('-MS').segments[-1].derivation_namespace == 'ACMELABS.COM'


# ---------------------------------------------------------------------------
# .issuing_system
# ---------------------------------------------------------------------------

def test_segment_issuing_system_is_none_when_no_issuing_system_present():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    ms = pac.get_category('-MS')
    assert ms.segments[-1].issuing_system is None
    assert ms.segments[0].issuing_system is None


def test_segment_issuing_system_matches_top_level_issuing_system_for_a_non_derived_segment():
    pac = from_url(valid_base + "-DR/21:1234/-PS/240:LABCROSS/+ACMELABS.COM/RECALC:1/-PS/240:ALIQUOT-TRACKER")
    primary = pac.get_category('-DR')
    non_derived_seg = primary.segments[0]  # 21:1234, before the marker
    assert non_derived_seg.issuing_system is not None
    assert non_derived_seg.issuing_system.processor_code == 'LABCROSS'


def test_segment_issuing_system_matches_scoped_issuing_system_for_a_derived_segment():
    pac = from_url(valid_base + "-DR/21:1234/-PS/240:LABCROSS/+ACMELABS.COM/RECALC:1/-PS/240:ALIQUOT-TRACKER")
    primary = pac.get_category('-DR')
    derived_seg = primary.segments[1]  # RECALC:1, added by ACMELABS.COM
    assert derived_seg.issuing_system is not None
    assert derived_seg.issuing_system.processor_code == 'ALIQUOT-TRACKER'


def test_segments_from_different_derivation_namespaces_get_different_issuing_systems():
    pac = from_url(
        "HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876"
        "/+ACMELABS.COM/250:1/-PS/240:TRACKER1"
        "/+OTHERLABS.COM/NOTE:2/-PS/240:TRACKER2"
    )
    primary = pac.get_category('-MS')
    by_value = {s.value: s for s in primary.segments}

    assert by_value['1'].issuing_system.processor_code == 'TRACKER1'
    assert by_value['2'].issuing_system.processor_code == 'TRACKER2'
    assert by_value['1'].issuing_system is not by_value['2'].issuing_system


def test_segment_issuing_system_is_stable_across_repeated_segments_access():
    ''' Regression guard for the "rebuilds fresh on every .segments access"
    gotcha (design-choices.md) - issuing_system must come back correctly even
    though the underlying segment objects are brand new on each read. '''
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1/-PS/240:ALIQUOT-TRACKER")
    ms = pac.get_category('-MS')
    first_read = ms.segments[-1].issuing_system
    second_read = ms.segments[-1].issuing_system  # fresh segment object, same category
    assert first_read is not None
    assert second_read is not None
    assert first_read.processor_code == second_read.processor_code == 'ALIQUOT-TRACKER'


def test_segment_issuing_system_not_included_in_serialization():
    pac = from_url(valid_base + "-DR/21:1234/-PS/240:LABCROSS/+ACMELABS.COM/RECALC:1/-PS/240:ALIQUOT-TRACKER")
    d = pac.to_dict()
    seg_dicts = d['categories'][0]['segments']
    assert all('issuing_system' not in s for s in seg_dicts)

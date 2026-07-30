'''
Tests for PAC-CAT's handling of derivation namespace segments (`+<namespace>`),
per the PAC-CAT spec section "Segments added via a derivation namespace (`+`)".

A derivation namespace segment lets a third party extend a PAC-ID (see PAC-ID spec,
"Issuing derived PAC-ID"s) while preserving clear attribution. Where PAC-CAT is used,
any category segments that follow a `+<namespace>` marker belong to the *primary*
category - they must not start a new category, and must not be attributed to a
second (issuing system) category, even if one appears between the primary category
and the marker.
'''
import pytest

from labfreed.pac_cat import PAC_CAT, Data_Result, Processor_Software


valid_base = "HTTPS://PAC.METTORIUS.COM/"


def from_url(url):
    return PAC_CAT.from_url(url, suppress_validation_errors=True)


def test_segment_after_marker_fills_a_known_field():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    ms = pac.get_category('-MS')
    assert ms.aliquot == '1'


def test_segment_after_marker_fills_a_known_field_short_notation():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/1")
    ms = pac.get_category('-MS')
    assert ms.aliquot == '1'


def test_marker_does_not_start_a_new_category():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    assert len(pac.categories) == 1

def test_get_non_derived_pac_id_preserves_pac_cat_type():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    root = pac.get_non_derived_pac_id()
    assert isinstance(root, PAC_CAT)
    assert root.get_category('-MS').product_number == 'AMYLASE'

def test_get_parent_pac_id_preserves_pac_cat_type():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    parent = pac.get_parent_pac_id()
    assert isinstance(parent, PAC_CAT)
    assert parent.get_category('-MS').product_number == 'AMYLASE'

def test_category_has_derivation_segments():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    ms = pac.get_category('-MS')
    assert ms.has_derivation_segments()

def test_category_has_derivation_segments_is_false_without_marker():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876")
    ms = pac.get_category('-MS')
    assert not ms.has_derivation_segments()

def test_category_segments_derived_by():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    ms = pac.get_category('-MS')
    derived = ms.segments_derived_by('ACMELABS.COM')
    assert [s.value for s in derived] == ['1']

def test_category_segments_derived_by_returns_empty_for_other_namespace():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    ms = pac.get_category('-MS')
    assert ms.segments_derived_by('SOMEONE-ELSE.COM') == []


# DECIDED: once every segment is tagged with the namespace that contributed it,
# the marker segment itself is redundant - it must not appear as its own entry in
# a category's `.segments`.
def test_marker_removed_from_segments():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    segs = pac.get_category('-MS').segments
    values = [s.value for s in segs]
    assert values == ['AMYLASE', 'AB9876', '500ML', '9876', '1']
    assert not any(s.is_derivation_namespace for s in segs)


def test_derivation_namespace_tagged_on_segment_after_marker():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1")
    segs = pac.get_category('-MS').segments
    # segments issued by the primary issuer (before the marker) carry no namespace
    assert [s.derivation_namespace for s in segs[:4]] == [None, None, None, None]
    # the segment the (now-removed) marker covered is tagged with it
    assert segs[4].derivation_namespace == 'ACMELABS.COM'


# default (non-forced) `to_url()` just echoes `pac.identifier` verbatim regardless of
# PAC-CAT - it doesn't go through `.segments` at all, so removing the marker there
# doesn't affect it. Kept mainly to document that this path is unaffected.
def test_round_trip_default_notation_preserves_marker_position():
    url_in = valid_base.replace('METTORIUS', 'OMNIZYME') + "-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1"
    pac = from_url(url_in)
    assert pac.to_url() == url_in


# Forced notation goes through `.segments`'s internal reconstruction too, but that
# reconstruction (`_get_segments`/`_get_segments_from_bindings`) keeps the marker
# internally even though the public `.segments` property hides it - so the marker is
# still correctly reproduced at its original position in forced-notation output.
def test_round_trip_forced_long_notation_preserves_marker_position():
    url_in = "HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1"
    pac = from_url(url_in)
    assert pac.to_url(use_short_notation=False) == url_in


def test_round_trip_forced_short_notation_preserves_marker_position():
    url_in = "HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/20:500ML/21:9876/+ACMELABS.COM/250:1"
    pac = from_url(url_in)
    expected = "HTTPS://PAC.OMNIZYME.COM/-MS/AMYLASE/AB9876/500ML/9876/+ACMELABS.COM/1"
    assert pac.to_url(use_short_notation=True) == expected


# kept: this covers the marker sitting inside a fully-implicit run from the very
# start of the category, not just after an explicit prefix.
def test_marker_does_not_break_implicit_key_sequence():
    # per spec: 'A +<namespace> marker does not interrupt the implicit key sequence'
    url_short = "HTTPS://PAC.OMNIZYME.COM/-MS/AMYLASE/AB9876/500ML/9876/+ACMELABS.COM/1"
    pac = from_url(url_short)
    assert pac.get_category('-MS').aliquot == '1'


def test_segments_after_marker_belong_to_primary_category_not_issuing_system():
    ''' Spec example: a result recalculated by a third party after it was recorded
    by an issuing system - the recalc segment still belongs to the *primary*
    category (-DR), not to the issuing system category (-PS) that precedes the marker. '''
    pac = from_url(valid_base + "-DR/21:1234/-PS/240:LABCROSS/+ACMELABS.COM/RECALC:1")
    assert len(pac.categories) == 2

    primary = pac.get_category('-DR')
    assert isinstance(primary, Data_Result)
    assert primary.id == '1234'
    values = [(s.key, s.value) for s in primary.segments]
    assert values == [('21', '1234'), ('RECALC', '1')]
    # the recalc segment is attributed to ACMELABS.COM even though it sits after -PS
    assert [s.derivation_namespace for s in primary.segments] == [None, 'ACMELABS.COM']

    issuing_system = pac.get_category('-PS')
    assert isinstance(issuing_system, Processor_Software)
    assert issuing_system.processor_code == 'LABCROSS'
    assert [(s.key, s.value) for s in issuing_system.segments] == [('240', 'LABCROSS')]
    assert issuing_system.segments[0].derivation_namespace is None


def test_round_trip_recalc_example():
    url_in = valid_base + "-DR/21:1234/-PS/240:LABCROSS/+ACMELABS.COM/RECALC:1"
    pac = from_url(url_in)
    assert pac.to_url() == url_in


# HARD REQUIREMENT: reparsing forced-notation output must never change the category
# structure. This is the recalc example: the marker's reattributed tail (+ACMELABS.COM/
# RECALC:1) is logically owned by -DR even though it sits textually after -PS. If forced
# notation is rebuilt by concatenating each category's own segments in `pac.categories`
# order, -DR's reattributed tail gets emitted before -PS - which puts `-PS` textually
# after a marker in the output, and reparsing that then wrongly redirects `-PS` itself
# into the primary category, collapsing two categories into one.
def test_forced_notation_never_changes_category_structure_across_a_marker():
    url_in = valid_base + "-DR/21:1234/-PS/240:LABCROSS/+ACMELABS.COM/RECALC:1"
    pac = from_url(url_in)
    for use_short_notation in (True, False):
        forced = pac.to_url(use_short_notation=use_short_notation)
        reparsed = from_url(forced)
        assert len(reparsed.categories) == 2, (
            f"use_short_notation={use_short_notation}: expected 2 categories after "
            f"reparsing {forced!r}, got {[c.key for c in reparsed.categories]}"
        )
        assert reparsed.get_category('-DR').id == '1234'
        assert reparsed.get_category('-PS').processor_code == 'LABCROSS'




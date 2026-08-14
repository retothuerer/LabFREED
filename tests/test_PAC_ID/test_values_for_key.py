'''
PAC_ID.values_for_key(key) / PAC_CAT.values_for_key(key) - joint lookup across
identifier segments and extensions, returning every match with provenance
rather than silently picking a winner. Collapses the field-notes brief's
separate "get-by-key" ask into this one method (filter by origin type for the
segment-only case).

KeyedValue.value is always a list, even for a single scalar match, so callers
never branch on scalar-vs-table before iterating. The list's items are
list[str] for segment/text-like matches, but a T-REX numeric match decodes to
Quantity (LabFREED has no unitless numbers - see CLAUDE.md), using the exact
same decode convention T_REX.from_trex() already uses (confirmed empirically:
even a unitless/C62 numeric decodes to Quantity, not a bare number).
KeyedValue.origin is
one of a small type hierarchy (SegmentOrigin/ExtensionOrigin/TrexTableOrigin),
not a flat "segment"/"trex" string - see design-choices.md ("values_for_key()'s
Origin types carry no describe()/custom __eq__...") for why: plain equality on
these origin types already answers "same place or not" correctly for free via
pydantic's default type+field equality, so tests below rely on == rather than
inspecting fields by hand.

Extension matching is polymorphic: ExtensionBase.values_for_key() is the
general default (matches self.name == key); TextBase36Extension overrides it
to return the decoded .text rather than the still-base36-encoded .data, so
DisplayNameExtension (a TextBase36Extension subclass, name fixed to 'N')
inherits a correct values_for_key('N') without its own override; TREX_Extension
overrides it to search its Spec_T_REX's segments *and* every TableSegment's
columns - required by the T-REX spec's own ENV/PH/CONDUCTIVITY example (see
design-choices.md), where "TEMP" is a repeated column key across three
top-level table segments within one extension, never a top-level segment key
itself.
'''
import pytest

from labfreed.pac_id import PAC_ID, IDSegment
from labfreed.pac_cat import PAC_CAT
from labfreed.pac_id.keyed_values import SegmentOrigin, ExtensionOrigin, TrexTableOrigin
from labfreed.well_known_extensions import TREX_Extension, DisplayNameExtension
from labfreed.trex.trex import Spec_T_REX
from labfreed.utilities.quantity import Quantity


def _env_ph_conductivity_trex_extension(name="SENSORS"):
    trex = Spec_T_REX.deserialize(
        "ENV$$PRESSURE$BAR:TEMP$KEL::1.01:293"
        "+PH$$PH$C62:TEMP$KEL::7.01:292"
        "+CONDUCTIVITY$$COND$SIE:TEMP$KEL::1.5:295"
    )
    return TREX_Extension(name=name, trex=trex)


def test_plain_pac_id_matches_an_explicit_segment_key():
    pac = PAC_ID(issuer="METTORIUS.COM", identifier=[IDSegment(key="10", value="BATCH1")])
    matches = pac.values_for_key("10")
    assert len(matches) == 1
    assert matches[0].value == ["BATCH1"]
    assert matches[0].origin == SegmentOrigin(category_key=None)


def test_plain_pac_id_does_not_resolve_implicit_keys():
    ''' Without category structure, there's no implicit key order to resolve against -
    an un-keyed segment simply can't match a specific key. '''
    pac = PAC_ID(issuer="METTORIUS.COM", identifier=[IDSegment(value="X67678"), IDSegment(value="BATCH1")])
    assert pac.values_for_key("10") == []


def test_pac_cat_resolves_an_implicit_segment_key():
    ''' -MS implies [240, 10, 20, 21, 250]; "BATCH1" lands in the 10 (batch) slot. '''
    pac = PAC_CAT.from_url("HTTPS://PAC.METTORIUS.COM/-MS/X67678/BATCH1", suppress_validation_errors=True)
    matches = pac.values_for_key("10")
    assert len(matches) == 1
    assert matches[0].value == ["BATCH1"]
    assert matches[0].origin == SegmentOrigin(category_key="-MS")


def test_no_match_returns_empty_list():
    pac = PAC_ID(issuer="METTORIUS.COM", identifier=[IDSegment(key="10", value="BATCH1")])
    assert pac.values_for_key("NOPE") == []


def test_display_name_extension_matches_by_name_with_decoded_text():
    ''' Must return the decoded display name, not the still-base36-encoded wire form -
    this is exactly what should let PacInfo.display_name's hardcoded
    get_extension('N').display_name step be replaced with values_for_key('N'). '''
    pac = PAC_ID(issuer="METTORIUS.COM", identifier=[IDSegment(value="X67678")])
    pac.extensions = [DisplayNameExtension(display_name="Hello")]
    matches = pac.values_for_key("N")
    assert len(matches) == 1
    assert matches[0].value == ["Hello"]
    assert matches[0].origin == ExtensionOrigin(extension_name="N")


def test_trex_extension_matches_a_scalar_segment():
    pac = PAC_ID(issuer="METTORIUS.COM", identifier=[IDSegment(value="X67678")])
    pac.extensions = [TREX_Extension(name="SENSORS", trex=Spec_T_REX.deserialize("TEMP$KEL:293"))]
    matches = pac.values_for_key("TEMP")
    assert len(matches) == 1
    assert matches[0].value == [Quantity(value=293, unit="K")]
    assert matches[0].origin == ExtensionOrigin(extension_name="SENSORS")


def test_trex_extension_matches_a_repeated_table_column_key_with_distinct_origins():
    ''' The T-REX spec's own example: "TEMP" repeats as a column key across three
    separate top-level table segments (ENV/PH/CONDUCTIVITY) within one extension.
    Spec_T_REX.get_segment("TEMP") alone would find nothing - "TEMP" is never a
    top-level segment key here. All three must come back, distinguishable by which
    table each came from. '''
    pac = PAC_ID(issuer="METTORIUS.COM", identifier=[IDSegment(value="X67678")])
    pac.extensions = [_env_ph_conductivity_trex_extension(name="SENSORS")]
    matches = pac.values_for_key("TEMP")
    assert len(matches) == 3
    by_table = {m.origin.table_key: m.value for m in matches}
    assert by_table == {
        "ENV": [Quantity(value=293, unit="K")],
        "PH": [Quantity(value=292, unit="K")],
        "CONDUCTIVITY": [Quantity(value=295, unit="K")],
    }
    assert all(isinstance(m.origin, TrexTableOrigin) for m in matches)
    assert all(m.origin.extension_name == "SENSORS" for m in matches)
    assert len({m.origin.table_key for m in matches}) == 3  # all three table_keys distinct


def test_joint_lookup_returns_both_segment_and_extension_matches_without_picking_a_winner():
    pac = PAC_CAT.from_url("HTTPS://PAC.METTORIUS.COM/-MS/X67678/10:LOT1", suppress_validation_errors=True)
    pac.extensions = [TREX_Extension(name="DOC", trex=Spec_T_REX.deserialize("10$T.A:LOT1B"))]
    matches = pac.values_for_key("10")
    assert len(matches) == 2
    origins = {type(m.origin).__name__ for m in matches}
    assert origins == {"SegmentOrigin", "ExtensionOrigin"}


def test_origin_equality_never_conflates_different_kinds_even_with_overlapping_fields():
    ''' Plain equality is the mechanism for "same place or not" - no describe()/custom
    __eq__ needed (see design-choices.md). A SegmentOrigin and an ExtensionOrigin must
    never compare equal even when both are otherwise "empty", because pydantic's default
    equality checks type as well as fields. '''
    assert SegmentOrigin(category_key=None) != ExtensionOrigin(extension_name="N")
    assert SegmentOrigin(category_key="-MS") == SegmentOrigin(category_key="-MS")
    assert SegmentOrigin(category_key="-MS") != SegmentOrigin(category_key="-MD")
    assert TrexTableOrigin(extension_name="X", table_key="ENV") != ExtensionOrigin(extension_name="X")
    assert TrexTableOrigin(extension_name="X", table_key="ENV") == TrexTableOrigin(extension_name="X", table_key="ENV")
    assert TrexTableOrigin(extension_name="X", table_key="ENV") != TrexTableOrigin(extension_name="X", table_key="PH")

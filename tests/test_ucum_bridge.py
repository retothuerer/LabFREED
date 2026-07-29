'''
Tests for labfreed.well_known_keys.unece.ucum_bridge - the automatic UNECE<->UCUM mapping.

Expected values below were verified empirically against the real bundled UneceUnits.json using
pint+ucumvert in a throwaway venv before writing these assertions (see
developer-docs/design-choices.md), not guessed.
'''
import pytest

from labfreed.well_known_keys.unece import ucum_bridge


# --- forward: Quantity's UCUM unit -> UNECE Common Code(s) ---------------------------------

def test_simple_si_unit_matches_its_unece_code():
    assert 'KGM' in ucum_bridge.unece_codes_for_ucum('kg')


def test_compound_unit_matches_all_physically_equal_unece_codes():
    # kg/m3 == g/L == g/dm3 as physical quantities - UCUM has no canonical form, so all three
    # UNECE codes for it are correct matches, not a bug.
    codes = ucum_bridge.unece_codes_for_ucum('kg/m3')
    assert set(codes) == {'KMQ', 'GL', 'F23'}


def test_molar_concentration_matches_expected_unece_code():
    assert 'C38' in ucum_bridge.unece_codes_for_ucum('mol/L')


def test_prefixed_molar_concentration_matches_expected_unece_code():
    assert 'M33' in ucum_bridge.unece_codes_for_ucum('mmol/L')


def test_celsius_matches_without_offset_unit_error():
    # pint raises OffsetUnitCalculusError for `1 * degree_Celsius` - the implementation must
    # build quantities via `ureg.Quantity(1, unit)` instead, or this raises rather than matching.
    assert ucum_bridge.unece_codes_for_ucum('Cel') == ['CEL']


def test_mass_concentration_with_micro_prefix_matches_expected_unece_codes():
    codes = ucum_bridge.unece_codes_for_ucum('ug/mL')
    assert set(codes) == {'A93', 'M1'}


def test_unece_codes_for_ucum_requires_units_extra(without_ucum_support):
    with pytest.raises(ucum_bridge.UcumSupportError):
        ucum_bridge.unece_codes_for_ucum('kg/m3')


# --- reverse: UNECE Common Code -> a valid UCUM unit ---------------------------------------

@pytest.mark.parametrize(("code", "expected_ucum"), [
    ('KGM', 'kg'),
    ('MTR', 'm'),
    ('MMT', 'mm'),
    ('CEL', 'Cel'),
    ('SEC', 's'),
])
def test_ucum_for_unece_code_normalizes_common_codes(code, expected_ucum):
    assert ucum_bridge.ucum_for_unece_code(code) == expected_ucum


def test_ucum_for_unece_code_raises_for_a_code_with_no_symbol_at_all():
    # commonCode '10' ("group") is a pure count unit with symbol=None in UneceUnits.json - there
    # is no UCUM equivalent, and there never will be, regardless of how the normalizer improves.
    with pytest.raises(ucum_bridge.UcumSupportError):
        ucum_bridge.ucum_for_unece_code('10')


# --- is_valid_ucum: authoritative when the extra is present, best-effort fallback otherwise --

def test_valid_compound_unit_is_accepted():
    assert ucum_bridge.is_valid_ucum('kg/m3') is True


@pytest.mark.parametrize("bad_unit", ["kg m3", "m^2"])
def test_blankspace_and_caret_are_rejected(bad_unit):
    assert ucum_bridge.is_valid_ucum(bad_unit) is False


@pytest.mark.parametrize("bad_unit", ["kg m3", "m^2"])
def test_blankspace_and_caret_are_rejected_without_units_extra(bad_unit, without_ucum_support):
    # the no-dependency fallback heuristic must catch these two common mistakes on its own -
    # it's exactly what today's regex in quantity.py already checks for.
    assert ucum_bridge.is_valid_ucum(bad_unit) is False


# --- pretty_print_ucum: extended-only convenience -------------------------------------------

def test_pretty_print_requires_units_extra(without_ucum_support):
    with pytest.raises(ucum_bridge.UcumSupportError):
        ucum_bridge.pretty_print_ucum('kg/m3')

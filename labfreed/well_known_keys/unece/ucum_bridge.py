'''@private
Bridge between UCUM unit strings (used by `Quantity` / PAC-ID Attributes) and UNECE Common Codes
(used by T-REX's wire format for `NumericSegment`/`ColumnHeader.type`).

`pint` and `ucumvert` are optional (the `units` extra) - this is the only module that imports
them. See developer-docs/design-choices.md for why, and what was verified empirically about
`UneceUnits.json`'s `parsedSymbol` field.
'''
import math
import re
from functools import lru_cache

from labfreed.well_known_keys.unece.unece_units import unece_unit, unece_units

try:
    from ucumvert import PintUcumRegistry
    HAS_UCUM_SUPPORT = True
except ImportError:
    HAS_UCUM_SUPPORT = False

_ureg = None


def _registry():
    global _ureg
    if _ureg is None:
        _ureg = PintUcumRegistry()
    return _ureg


class UcumSupportError(ImportError):
    '''Raised when a UCUM<->UNECE operation needs the optional 'units' extra and it is not installed.'''
    def __init__(self, message: str):
        super().__init__(f"{message} Install with: pip install labfreed[units]")


_SUPERSCRIPT_TRANSLATION = str.maketrans('²³⁴⁻¹⁰', '234-10')


def _normalize_unece_symbol(symbol: str) -> str:
    '''Best-effort rewrite of a UNECE display symbol into UCUM syntax (superscript digits,
    the middle dot, µ, and the two non-ASCII temperature symbols UNECE uses).'''
    s = symbol.translate(_SUPERSCRIPT_TRANSLATION)
    s = s.replace('·', '.')
    s = s.replace('°C', 'Cel').replace('°F', '[degF]')
    s = s.replace('µ', 'u').replace('Ω', '[ohm]')
    s = s.replace(' ', '')
    return s


# Loose "does this look like UCUM" check used when the units extra isn't installed - not
# authoritative, just catches the common mistakes (blankspace, '^' for exponents).
_FALLBACK_UCUM_PATTERN = re.compile(
    r"^(((?P<unit>[\w\[\]]+?)(?P<exponent>\-?\d+)?|(?P<annotation>)\{\w+?\})(?P<operator>[\./]?)?)+"
)


def _is_valid_ucum_fallback(unit: str) -> bool:
    if ' ' in unit or '^' in unit:
        return False
    return bool(_FALLBACK_UCUM_PATTERN.fullmatch(unit))


def is_valid_ucum(unit: str) -> bool:
    '''Whether `unit` is a syntactically valid UCUM expression.

    Authoritative (parses via ucumvert/pint) when HAS_UCUM_SUPPORT; otherwise falls back to a
    best-effort heuristic requiring no dependency.
    '''
    if HAS_UCUM_SUPPORT:
        try:
            _registry().from_ucum(unit)
            return True
        except Exception:
            return False
    return _is_valid_ucum_fallback(unit)


@lru_cache(maxsize=1)
def _unece_physical_quantities():
    '''Every active UNECE code's physical quantity, built from its already-embedded
    `parsedSymbol` field (confirmed empirically to be pint expression syntax).'''
    ureg = _registry()
    quantities = {}
    for u in unece_units():
        if u.get('state') != 'ACTIVE':
            continue
        parsed_symbol = u.get('parsedSymbol')
        if not parsed_symbol:
            continue
        try:
            quantities[u['commonCode']] = ureg.parse_expression(parsed_symbol)
        except Exception:
            continue
    return quantities


def unece_codes_for_ucum(unit: str) -> list[str]:
    '''All UNECE Common Codes that are physically equal to the given UCUM unit.

    Requires HAS_UCUM_SUPPORT - raises UcumSupportError otherwise.
    '''
    if not HAS_UCUM_SUPPORT:
        raise UcumSupportError(f"Cannot automatically resolve UNECE code(s) for UCUM unit {unit!r}.")

    ureg = _registry()
    target = ureg.from_ucum(unit).to_base_units()

    matches = []
    for code, quantity in _unece_physical_quantities().items():
        try:
            base = quantity.to_base_units()
        except Exception:
            continue
        if base.dimensionality == target.dimensionality and math.isclose(
            base.magnitude, target.magnitude, rel_tol=1e-9, abs_tol=1e-12
        ):
            matches.append(code)
    return matches


def best_unece_code_for_ucum(unit: str) -> str:
    '''A single UNECE Common Code for the given UCUM unit, deterministically chosen when more
    than one code is physically equal (UCUM has no canonical form, so this is common for
    compound units): prefer a code whose own symbol normalizes back to the input, else prefer
    a LEVEL_1_NORMATIVE code, else the lexicographically lowest commonCode.
    '''
    codes = unece_codes_for_ucum(unit)
    if not codes:
        raise UcumSupportError(f"No UNECE code found for UCUM unit {unit!r}.")
    if len(codes) == 1:
        return codes[0]

    def own_symbol_matches(code):
        entry = unece_unit(code) or {}
        symbol = entry.get('symbol')
        return bool(symbol) and _normalize_unece_symbol(symbol) == unit

    exact = sorted(c for c in codes if own_symbol_matches(c))
    if exact:
        return exact[0]

    def is_normative(code):
        entry = unece_unit(code) or {}
        return 'LEVEL_1_NORMATIVE' in (entry.get('categories') or '')

    normative = sorted(c for c in codes if is_normative(c))
    if normative:
        return normative[0]

    return sorted(codes)[0]


def ucum_for_unece_code(code: str) -> str:
    '''A valid UCUM expression for the given UNECE Common Code, derived by normalizing UNECE's
    own `symbol` field.

    Raises UcumSupportError if the code has no symbol, or its symbol can't be automatically
    translated to valid UCUM - gaps are meant to be filled by hand only once actually hit
    (see developer-docs/TODO.md), not curated upfront.
    '''
    entry = unece_unit(code)
    symbol = entry.get('symbol') if entry else None
    if not symbol:
        raise UcumSupportError(f"No UCUM equivalent is known for UNECE code {code!r}.")

    candidate = _normalize_unece_symbol(symbol)
    if is_valid_ucum(candidate):
        return candidate

    raise UcumSupportError(
        f"UNECE code {code!r}'s symbol {symbol!r} could not be automatically translated to UCUM."
    )


def pretty_print_ucum(unit: str) -> str:
    '''Human-readable rendering of a UCUM unit (e.g. for display, not for wire format).

    Requires HAS_UCUM_SUPPORT - raises UcumSupportError otherwise.
    '''
    if not HAS_UCUM_SUPPORT:
        raise UcumSupportError(f"Cannot pretty-print UCUM unit {unit!r} automatically.")
    q = _registry().from_ucum(unit)
    return f'{q.units:~P}'

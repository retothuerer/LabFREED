'''@private
Bridge between UCUM unit strings (used by `Quantity` / PAC-ID Attributes) and UNECE Common Codes
(used by T-REX's wire format for `NumericSegment`/`ColumnHeader.type`).

`pint` and `ucumvert` are optional (the `units` extra) - this is the only module that imports
them. See developer-docs/design-choices.md for why, and what was verified empirically about
`UneceUnits.json`'s `parsedSymbol` field before this module's functions were implemented.

STUB: function bodies are not yet implemented (test-first - see tests/test_ucum_bridge.py, still
marked NOT REVIEWED). Only the soft-import scaffolding is real.
'''

try:
    from ucumvert import PintUcumRegistry  # noqa: F401
    HAS_UCUM_SUPPORT = True
except ImportError:
    HAS_UCUM_SUPPORT = False


class UcumSupportError(ImportError):
    '''Raised when a UCUM<->UNECE operation needs the optional 'units' extra and it is not installed.'''
    def __init__(self, message: str):
        super().__init__(f"{message} Install with: pip install labfreed[units]")


def is_valid_ucum(unit: str) -> bool:
    '''Whether `unit` is a syntactically valid UCUM expression.

    Authoritative (parses via ucumvert/pint) when HAS_UCUM_SUPPORT; otherwise falls back to a
    best-effort heuristic requiring no dependency.
    '''
    raise NotImplementedError


def unece_codes_for_ucum(unit: str) -> list[str]:
    '''All UNECE Common Codes that are physically equal to the given UCUM unit.

    Requires HAS_UCUM_SUPPORT - raises UcumSupportError otherwise.
    '''
    raise NotImplementedError


def ucum_for_unece_code(code: str) -> str:
    '''A valid UCUM expression for the given UNECE Common Code.

    Raises UcumSupportError if no UCUM equivalent can be determined for this code.
    '''
    raise NotImplementedError


def pretty_print_ucum(unit: str) -> str:
    '''Human-readable rendering of a UCUM unit (e.g. for display, not for wire format).

    Requires HAS_UCUM_SUPPORT - raises UcumSupportError otherwise.
    '''
    raise NotImplementedError

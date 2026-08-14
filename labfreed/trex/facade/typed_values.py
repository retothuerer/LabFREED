from datetime import date, datetime, time

from pydantic import RootModel, field_validator


class Alphanumeric(RootModel[str]):
    '''Forces the T-REX T.A (alphanumeric) wire type, instead of leaving the choice
    between T.A and T.T to the auto-detect charset check. Validates eagerly against
    the same charset AlphanumericSegment itself enforces, so misuse fails loud at
    construction time rather than being silently reinterpreted as T.T.'''

    @field_validator('root')
    @classmethod
    def _validate_charset(cls, v: str) -> str:
        import re
        if not re.fullmatch(r'[A-Z0-9\-\.]*', v):
            raise ValueError(
                "Alphanumeric value must only contain uppercase letters, digits, '-' and '.' "
                "(A-Z, 0-9, -, .)"
            )
        return v


class Text(RootModel[str]):
    '''Forces the T-REX T.T (text) wire type. Takes ordinary, human-readable text and
    encodes it to base36 internally at serialization time - unlike `base36`, which
    requires its input to already be base36-encoded and would reject plain text.'''


class Numeric(RootModel[int | float]):
    '''Forces the T-REX numeric wire type. No real ambiguity exists for a bare
    int/float today (they already dispatch unambiguously) - this wrapper exists for
    explicit-typing symmetry with Alphanumeric/Text/Bool/Date.'''


class Bool(RootModel[bool]):
    '''Forces the T-REX T.B (bool) wire type. No real ambiguity exists for a bare
    bool today - this wrapper exists for explicit-typing symmetry.'''


class Date(RootModel[date | time | datetime]):
    '''Forces the T-REX T.D (date) wire type. No real ambiguity exists for a bare
    date/time/datetime today - this wrapper exists for explicit-typing symmetry.'''

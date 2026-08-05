from typing import Literal
from pydantic import BaseModel, ConfigDict


class HPStatement(BaseModel):
    '''Frozen so pydantic derives __hash__ from field values automatically - these
    go into a set() in PacInfo.hazard_statements/precautionary_statements.'''
    model_config = ConfigDict(frozen=True)

    code: str
    # None until predefined-lookup coverage or attribute-delivered text closes the gap
    # (e.g. EUH-codes, not in the UNECE Annex 3 table this is currently sourced from)
    text: str | None
    text_origin: Literal['Attribute', 'Predefined']
    # None alongside text=None - completeness is only known once the Annex 3 lookup
    # resolves the statement's text (see ghs_statements.*_statement_is_complete)
    complete: bool | None = None


class HazardStatement(HPStatement):
    ...


class PrecautionaryStatement(HPStatement):
    ...

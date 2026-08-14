from abc import ABC

from labfreed.labfreed_infrastructure import LabFREED_BaseModel


class Origin(LabFREED_BaseModel, ABC):
    '''Where a KeyedValue came from - a small type hierarchy rather than a closed
    "segment"/"trex" string, so a match can say *which* category/extension/table it
    came from, and so a future third source (e.g. PAC-ID Attributes) can be added as
    another subtype without reinventing the concept. No methods of its own: plain
    equality already answers "same place or not" correctly for free (pydantic's
    default equality checks type as well as fields), and __repr__/__str__ already
    show every field for free too - see design-choices.md.'''


class SegmentOrigin(Origin):
    category_key: str | None
    '''The PAC-CAT category key (e.g. "-MS") this segment belongs to, or None for a
    plain, non-category IDSegment.'''


class ExtensionOrigin(Origin):
    extension_name: str


class TrexTableOrigin(ExtensionOrigin):
    table_key: str
    '''The T-REX TableSegment's own top-level key (e.g. "ENV") - distinct from the
    column key being matched, which is the key values_for_key() was called with.'''


class KeyedValue(LabFREED_BaseModel):
    '''One match from PAC_ID.values_for_key()/PAC_CAT.values_for_key(). value is
    always a list, even for a single scalar match, so callers never branch on
    scalar-vs-table before iterating - a table-column match's value is that column's
    full list of decoded values, not one row-indexed scalar.'''
    value: list
    origin: Origin

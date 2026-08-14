
import re
from typing import Any
from pydantic import PrivateAttr, computed_field, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel
from labfreed.pac_id.id_segment import IDSegment
from labfreed.pac_id.keyed_values import KeyedValue, SegmentOrigin


_category_key_pattern = r'-[A-Za-z]+'


class CategorySegment(IDSegment):
    ''' An id segment as it appears within a PAC-CAT category, tagged with which
    derivation namespace (if any) contributed it - see PAC-CAT "Segments added via
    a derivation namespace" section.

    `derivation_namespace`/`issuer`/`issuing_system` are all private-attr-backed,
    Python-only convenience - none of the three are constructor kwargs, and none
    are part of serialization (`to_dict()`/the Resolver Context JSON). They're
    wired in by `PAC_CAT` (`_cat_from_cat_segments`, `_partition_categories`)
    after parsing, not set directly by callers. '''
    _derivation_namespace: str | None = PrivateAttr(default=None)
    _issuer: str = PrivateAttr(default=None)
    _issuing_system: 'Category | None' = PrivateAttr(default=None)

    @property
    def derivation_namespace(self) -> str | None:
        ''' The namespace that added this segment via a `+<namespace>` marker (without
        the leading `+`), or None if it was part of the identifier as issued by the
        primary issuer. The marker segment itself never appears as its own entry in a
        category's `.segments` - once every segment is tagged, it would just be
        redundant noise. '''
        return self._derivation_namespace

    @property
    def issuer(self) -> str:
        ''' The domain that added this segment - `derivation_namespace` if it was
        added via a `+<namespace>` marker, otherwise the PAC-ID's own issuer. '''
        return self._derivation_namespace or self._issuer

    @property
    def issuing_system(self) -> 'Category | None':
        ''' The issuing-system category scoped to this segment's own derivation
        (or the PAC-ID's own top-level issuing system, if this segment wasn't
        added via a derivation namespace) - see PAC-CAT "Identifying the issuing
        system of a derivation" and `PAC_CAT.derivation_issuing_systems`. None if
        no such category is present. '''
        return self._issuing_system


class Category(LabFREED_BaseModel):
    '''
    Represents a category. \n
    This is the base class for categories. If possible a more specific category should be used.
    '''
    key:str
    '''The category key, e.g. "-MD"'''
    _segments: list[CategorySegment] = PrivateAttr(default_factory=list)
    _derivation_namespace: str | None = PrivateAttr(default=None)
    _issuer: str = PrivateAttr(default=None)
    _issuing_systems_by_scope: dict = PrivateAttr(default_factory=dict)
    ''' @private Only meaningfully populated on the primary category
    (`PAC_CAT._partition_categories`) - maps a derivation namespace (or `None`
    for the PAC-ID's own top-level issuing system) to the `Category` a segment
    with that `derivation_namespace` should report as `.issuing_system`. '''

    @computed_field
    @property
    def segments(self) -> list[CategorySegment]:
        return self._segments

    @property
    def derivation_namespace(self) -> str | None:
        ''' Which `+<namespace>` block this category is scoped to, if it is an
        issuing-system category for one specific derivation (PAC-CAT
        "Identifying the issuing system of a derivation") - `None` for the
        primary category and for the PAC-ID's own top-level issuing system. '''
        return self._derivation_namespace

    def has_derivation_segments(self) -> bool:
        '''Whether any segment in this category was added via a derivation
        namespace (`+<namespace>`) by a third party, rather than by the original
        issuer. See PAC-CAT spec, "Segments added via a derivation namespace".'''
        return any(s.derivation_namespace for s in self.segments)

    def segments_derived_by(self, namespace: str) -> list[CategorySegment]:
        '''The segments in this category that were added by the given derivation
        namespace (`namespace`, without the leading `+`).'''
        return [s for s in self.segments if s.derivation_namespace == namespace]

    def value_for_key(self, key: str) -> KeyedValue | None:
        '''This category's own value for a raw key (explicit or implicit alias), as a
        KeyedValue tagged with this category's own key - or None if not present.
        Checks .segments directly, which is already the correct source of truth
        regardless of whether the original wire form spelled the key out explicitly
        or relied on position (PredefinedCategory's .segments always reports explicit
        keys - see design-choices.md).'''
        for seg in self.segments:
            if seg.key == key:
                return KeyedValue(value=[seg.value], origin=SegmentOrigin(category_key=self.key))
        return None

    @classmethod
    def from_key(cls, key: str, **fields) -> 'Category':
        '''Builds a category from a raw category-key string (e.g. "-MS") plus
        alias-keyed fields (e.g. {"240": "X67678", "10": "BATCH1"}), for callers who'd
        rather pass a key string than import the concrete PredefinedCategory subclass.
        None-valued fields are dropped, matching how an omitted optional field already
        behaves. Falls back to a plain, generic Category for an unregistered key,
        mirroring PAC_CAT._cat_from_cat_segments's own fallback.'''
        from labfreed.pac_cat.predefined_categories import category_key_to_class_map
        fields = {k: v for k, v in fields.items() if v is not None}
        known_cat = category_key_to_class_map.get(key)
        if known_cat:
            return known_cat(**fields)
        return Category(key=key, segments=[CategorySegment(key=k, value=v) for k, v in fields.items()])

    @classmethod
    def of(cls, key: str, **fields) -> 'Category':
        '''Alias for from_key() - from_key is the encouraged spelling (matches this
        codebase's from_* convention); of is provided for callers coming from Java/
        TS-influenced ecosystems, where that's the idiomatic name.'''
        return cls.from_key(key, **fields)

    def __init__(self, **data: Any):
        '''@private'''
        # Pop the user-provided value for computed segments
        input_segments = data.pop("segments", None)
        super().__init__(**data)
        self._segments = input_segments
    
    @model_validator(mode='after')
    def _warn_unusual_category_key(self):
        ''' this base class is instantiated only if the key is not a known category key'''
        if type(self) is Category:
            self._add_validation_message(
                        source=f"Category {self.key}",
                        level = ValidationMsgLevel.RECOMMENDATION,
                        msg=f'Category key {self.key} is not a well known key. It is recommended to use well known keys only',
                        highlight_pattern = f"{self.key}"
            )
        return self

    @model_validator(mode='after')
    def _validate_key_format(self):
        ''' PAC-CAT: "The category key MUST start with a -, followed by the at least one letter." '''
        if not re.fullmatch(_category_key_pattern, self.key):
            self._add_validation_message(
                        source=f"Category {self.key}",
                        level = ValidationMsgLevel.ERROR,
                        msg=f"Category key '{self.key}' is invalid. It MUST start with '-' followed by at least one letter.",
                        highlight_pattern = f"{self.key}"
            )
        return self
    
    
    def __str__(self):
        s = '\n'.join( [f"{field_name} \t ({field_info.alias or ''}): \t {getattr(self, field_name)}" for  field_name, field_info in type(self).model_fields.items() if getattr(self, field_name)])
        return s 
    
    def segments_as_dict(self, include_alias=False):
        ''' returns the segments in a dict, with nice keys and values'''
        out = dict()
        for  field_name, field_info in type(self).model_fields.items():
            if field_name =='additional_segments':
                continue
            if v := getattr(self, field_name):
                if field_info.alias and include_alias:
                    k = f"{field_name} ({ field_info.alias})"
                else:
                    k = f"{field_name}"
                out.update({k : v } ) 
            
        for s in getattr(self, 'additional_segments', []):
            out.update( {s.key or '' : s.value })
        return out

        







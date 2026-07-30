
import re
from typing import Any
from pydantic import PrivateAttr, computed_field, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel
from labfreed.pac_id.id_segment import IDSegment


_category_key_pattern = r'-[A-Za-z]+'


class CategorySegment(IDSegment):
    ''' An id segment as it appears within a PAC-CAT category, tagged with which
    derivation namespace (if any) contributed it - see PAC-CAT "Segments added via
    a derivation namespace" section. '''
    derivation_namespace: str | None = None
    ''' The namespace that added this segment via a `+<namespace>` marker (without the
    leading `+`), or None if it was part of the identifier as issued by the primary
    issuer. The marker segment itself never appears as its own entry in a category's
    `.segments` - once every segment is tagged, it would just be redundant noise. '''


class Category(LabFREED_BaseModel):
    '''
    Represents a category. \n
    This is the base class for categories. If possible a more specific category should be used.
    '''
    key:str
    '''The category key, e.g. "-MD"'''
    _segments: list[CategorySegment] = PrivateAttr(default_factory=list)


    @computed_field
    @property
    def segments(self) -> list[CategorySegment]:
        return self._segments

    def has_derivation_segments(self) -> bool:
        '''Whether any segment in this category was added via a derivation
        namespace (`+<namespace>`) by a third party, rather than by the original
        issuer. See PAC-CAT spec, "Segments added via a derivation namespace".'''
        return any(s.derivation_namespace for s in self.segments)

    def segments_derived_by(self, namespace: str) -> list[CategorySegment]:
        '''The segments in this category that were added by the given derivation
        namespace (`namespace`, without the leading `+`).'''
        return [s for s in self.segments if s.derivation_namespace == namespace]

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

        







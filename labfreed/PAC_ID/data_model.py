import re
from typing import Optional
from typing_extensions import Self
from pydantic import Field, ValidationInfo, computed_field, conlist, model_validator, field_validator
from ..validation import BaseModelWithWarnings, ValidationWarning, hsegment_pattern, domain_name_pattern
from abc import ABC, abstractproperty, abstractstaticmethod
from .well_known_segment_keys import WellKnownSegmentKeys


class IDSegment(BaseModelWithWarnings):
    key:str|None = None
    value:str  
    @model_validator(mode="after")
    def validate_segment(cls, model):
        key = model.key or ""
        value = model.value 
        
        # MUST be a valid hsegment according to RFC 1738, but without * (see PAC-ID Extension)
        # This means it must be true for both, key and value
        if not_allowed_chars := set(re.sub(hsegment_pattern, '', key)):
            raise ValueError(f"id segment key {key} contains invalid characters {' '.join(not_allowed_chars)}.")
        
        if not_allowed_chars := set(re.sub(hsegment_pattern, '', value)):
            raise ValueError(f"id segment key {value} contains invalid characters {' '.join(not_allowed_chars)}.")

        # Segment key SHOULD be limited to A-Z, 0-9, and -+..
        if not_recommended_chars := set(re.sub(r'[A-Z0-9-:+]', '', key)):
            model.add_warning(
                    source=f"id segment key {key}",
                    type="Recommendation",
                    msg=f"{' '.join(not_recommended_chars)} should not be used.",
                    recommendation = "SHOULD be limited to A-Z, 0-9, and -+",
                    highlight_pattern = key,
                    highlight_sub = not_recommended_chars
                )
            
        # Segment key should be in Well know keys
        if key and key not in [k.value for k in WellKnownSegmentKeys]:
            model.add_warning(
                    source=f"id segment key {key}",
                    type="Recommendation",
                    msg=f"{key} is not a well known segment key.",
                    recommendation = "RECOMMENDED to be a well-known id segment key.",
                    highlight_pattern = key
                )
            
            
        # Segment value SHOULD be limited to A-Z, 0-9, and -+..
        if not_recommended_chars := set(re.sub(r'[A-Z0-9-:+]', '', value)):
            model.add_warning(
                    source=f"id segment value {value}",
                    type="Recommendation",
                    msg=f"Characters {' '.join(not_recommended_chars)} should not be used.",
                    recommendation = "SHOULD be limited to A-Z, 0-9, and -+",
                    highlight_pattern = value,
                    highlight_sub = not_recommended_chars
                )
            
        # Segment value SHOULD be limited to A-Z, 0-9, and :-+ for new designs.
        # this means that ":" in key or value is problematic
        if ':' in key:
            model.add_warning(
                    source=f"id segment key {key}",
                    type="Recommendation",
                    msg=f"Character ':' should not be used in segment key, since this character is used to separate key and value this can lead to undefined behaviour.",
                    highlight_pattern = key
                )
        if ':' in value:
            model.add_warning(
                    source=f"id segment value {value}",
                    type="Recommendation",
                    msg=f"Character ':' should not be used in segment value, since this character is used to separate key and value this can lead to undefined behaviour.",
                    highlight_pattern = value
                )
                
        return model
    
  
    

class Category(BaseModelWithWarnings):
    key:str|None = None
    segments: list[IDSegment]


class Identifier(BaseModelWithWarnings):
    segments: conlist(IDSegment, min_length=1) = Field(..., exclude=True) # type: ignore # exclude=True prevents this from being serialized by Pydantic
        
    @computed_field
    @property
    def categories(self) -> list[Category]:
        categories = list()
        c = Category(segments=[])
        categories.append(c)
        for s in self.segments:
            # new category starts with "-"
            if s.value[0] == '-':
                cat_key = s.value
                c = Category(key=cat_key, segments=[])
                categories.append(c)
            else:
                c.segments.append(s)
            
        # the first category might have no segments. remove categories without segments
        if not categories[0].segments:
            categories = categories[1:]
                
        return categories
    
    @model_validator(mode='after')
    def check_keys_are_unique_in_each_category(self) -> Self:
        for c in self.categories:
            keys = [s.key for s in c.segments if s.key]
            duplicate_keys = [k for k in set(keys) if keys.count(k) > 1]
            if duplicate_keys:
                raise ValueError(f'Duplicate keys {",".join(duplicate_keys)} in category {c.key}')
            return self
        
    @model_validator(mode='after')
    def check_length(self) -> Self:
        l = 0
        for s in self.segments:
            if s.key:
                l += len(s.key)
                l += 1 # for ":"
            l += len(s.value)
        l += len(self.segments) - 1 # account for "/" separating the segments
        
        if l > 256:
            raise ValueError(f'Identifier is {l} characters long, Identifier must not exceed 256 characters.')
        return self
       
    @staticmethod 
    def from_categories(categories:list[Category]) :
        segments = list()
        for c in categories:
            if c.key:
                segments.append(IDSegment(value=c.key))
            segments.extend(c.segments)
        return Identifier(segments=segments)
        
    

class Extension(ABC, BaseModelWithWarnings): 
    
    @abstractproperty
    def name(self)->str:
        pass
    
    @abstractproperty
    def type(self)->str:
        pass
    
    @abstractproperty
    def data(self)->str:
        pass
    
    @abstractstaticmethod
    def from_spec_fields(name, type, data):
        pass
    
    
class UnknownExtension(Extension):
    name_:str
    type_:str
    data_:str
    
    @property
    def name(self)->str:
        return self.name_
    
    @property
    def type(self)->str:
        return self.type_
    
    @property
    def data(self)->str:
        return self.data_
       
    @staticmethod
    def from_spec_fields(name, type, data):
        return UnknownExtension(name_=name, type_=type, data_=data)
    


class PACID(BaseModelWithWarnings):
    issuer:str
    identifier: Identifier
    
    @model_validator(mode="after")
    def validate_issuer(cls, model):
        if not re.fullmatch(domain_name_pattern, model.issuer):
            raise ValueError("Issuer must be a valid domain name.")

         
        # recommendation that A-Z, 0-9, -, and . should be used
        if not_recommended_chars := set(re.sub(r'[A-Z0-9\.-]', '', model.issuer)):
            model.add_warning(
                    source="PAC-ID",
                    type="Recommendation",
                    highlight_pattern=model.issuer,
                    highlight_sub=not_recommended_chars,
                    msg=f"Characters {' '.join(not_recommended_chars)} should not be used. Issuer SHOULD contain only the characters A-Z, 0-9, -, and . "
                )
        return model
    
    
class PACID_With_Extensions(BaseModelWithWarnings):
    pac_id: PACID
    extensions: list[Extension] = Field(default_factory=list)






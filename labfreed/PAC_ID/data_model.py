import re
from typing import Optional
from typing_extensions import Self
from pydantic import Field, ValidationInfo, computed_field, conlist, model_validator, field_validator

from abc import ABC, abstractproperty, abstractstaticmethod

from ..utilities.well_known_keys import WellKnownKeys
from labfreed.validation import LabFREED_BaseModel, ValidationMessage, ValidationMsgLevel, quote_texts, hsegment_pattern, domain_name_pattern


class IDSegment(LabFREED_BaseModel):
    key:str|None = None
    value:str  
    
    @model_validator(mode="after")
    def validate_segment(self):
        key = self.key or ""
        value = self.value 
        
        # MUST be a valid hsegment according to RFC 1738, but without * (see PAC-ID Extension)
        # This means it must be true for both, key and value
        if not_allowed_chars := set(re.sub(hsegment_pattern, '', key)):
            self.add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"{quote_texts(not_allowed_chars)} must not be used. The segment key must be a valid hsegment",
                    highlight_pattern = key,
                    highlight_sub = not_allowed_chars
            )
        
        if not_allowed_chars := set(re.sub(hsegment_pattern, '', value)):
            self.add_validation_message(
                    source=f"id segment key {value}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"{quote_texts(not_allowed_chars)} must not be used. The segment key must be a valid hsegment",
                    highlight_pattern = value,
                    highlight_sub = not_allowed_chars
            )

        # Segment key SHOULD be limited to A-Z, 0-9, and -+..
        if not_recommended_chars := set(re.sub(r'[A-Z0-9-:+]', '', key)):
            self.add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"{quote_texts(not_recommended_chars)} should not be used. Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+' ",
                    highlight_pattern = key,
                    highlight_sub = not_recommended_chars
                )
            
        # Segment key should be in Well know keys
        if key and key not in [k.value for k in WellKnownKeys]:
            self.add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"{key} is not a well known segment key. It is RECOMMENDED to use well-known keys.",
                    highlight_pattern = key,
                    highlight_sub=[key]
                )
            
            
        # Segment value SHOULD be limited to A-Z, 0-9, and -+..
        if not_recommended_chars := set(re.sub(r'[A-Z0-9-:+]', '', value)):
            self.add_validation_message(
                    source=f"id segment value {value}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"Characters {quote_texts(not_recommended_chars)} should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+' ",
                    highlight_pattern = value,
                    highlight_sub = not_recommended_chars
                )
            
        # Segment value SHOULD be limited to A-Z, 0-9, and :-+ for new designs.
        # this means that ":" in key or value is problematic
        if ':' in key:
            self.add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"Character ':' should not be used in segment key, since this character is used to separate key and value this can lead to undefined behaviour.",
                    highlight_pattern = key
                )
        if ':' in value:
            self.add_validation_message(
                    source=f"id segment value {value}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"Character ':' should not be used in segment value, since this character is used to separate key and value this can lead to undefined behaviour.",
                    highlight_pattern = value
                )
                
        return self
     
  

class PACID(LabFREED_BaseModel):
    issuer:str
    identifier: conlist(IDSegment, min_length=1) = Field(..., default_factory=list) # type: ignore # exclude=True prevents this from being serialized by Pydantic
        
        
    @model_validator(mode='after')
    def check_length(self) -> Self:
        l = 0
        for s in self.identifier:
            s:IDSegment = s
            if s.key:
                l += len(s.key)
                l += 1 # for ":"
            l += len(s.value)
        l += len(self.identifier) - 1 # account for "/" separating the segments
        
        if l > 256:
            self.add_validation_message(
                        source=f"identifier",
                        level = ValidationMsgLevel.ERROR,
                        msg=f'Identifier is {l} characters long, Identifier must not exceed 256 characters.'
                    )
        return self
       
    
    @model_validator(mode="after")
    def validate_issuer(self):
        if not re.fullmatch(domain_name_pattern, self.issuer):
            self.add_validation_message(
                    source="PAC-ID",
                    level = ValidationMsgLevel.ERROR,
                    highlight_pattern=self.issuer,
                    msg=f"Issuer must be a valid domain name. "
                )
         
        # recommendation that A-Z, 0-9, -, and . should be used
        if not_recommended_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.issuer)):
            self.add_validation_message(
                    source="PAC-ID",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    highlight_pattern=self.issuer,
                    highlight_sub=not_recommended_chars,
                    msg=f"Characters {' '.join(not_recommended_chars)} should not be used. Issuer SHOULD contain only the characters A-Z, 0-9, -, and . "
                )
        return self
    
    
    @model_validator(mode='after')
    def check_identifier_segment_keys_are_unique(self) -> Self:
        keys = [s.key for s in self.identifier if s.key]
        duplicate_keys = [k for k in set(keys) if keys.count(k) > 1]
        if duplicate_keys:
            for k in duplicate_keys:
                self.add_validation_message(
                    source=f"identifier {k}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"Duplicate segment key {k}. This will probably lead to undefined behaviour",
                    highlight_pattern = k
                )
        return self
    
    
    def __str__(self):
        id_segments = ''
        for s in self.identifier:
            s:IDSegment = s
            if s.key:
                id_segments += f'/{s.key}:{s.value}'
            else:
                id_segments += f'/{s.value}'
    
        out = f"HTTPS://PAC.{self.issuer}{id_segments}"
        return out
    
    
    def serialize(self):
        return str(self)
    
    


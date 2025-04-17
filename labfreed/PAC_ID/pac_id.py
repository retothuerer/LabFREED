import re
from typing_extensions import Self
from pydantic import Field, conlist, model_validator


from ..well_known_keys.labfreed_common_keys.well_known_keys import WellKnownKeys
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel, _quote_texts

_domain_name_pattern = r"(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}"
_hsegment_pattern = r"[A-Za-z0-9_\-\.~!$&'()+,:;=@]|%[0-9A-Fa-f]{2}"

class IDSegment(LabFREED_BaseModel):
    """ Represents an id segment of a PAC-ID. It can be a value or a key value pair.
    """
    key:str|None = None
    ''' The key of the segment. This is optional.'''
    value:str  
    ''' The value of the segment. (mandatory)'''
    
    @model_validator(mode="after")
    def _validate_segment(self):
        key = self.key or ""
        value = self.value 
        
        # MUST be a valid hsegment according to RFC 1738, but without * (see PAC-ID Extension)
        # This means it must be true for both, key and value
        if not_allowed_chars := set(re.sub(_hsegment_pattern, '', key)):
            self._add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"{_quote_texts(not_allowed_chars)} must not be used. The segment key must be a valid hsegment",
                    highlight_pattern = key,
                    highlight_sub = not_allowed_chars
            )
        
        if not_allowed_chars := set(re.sub(_hsegment_pattern, '', value)):
            self._add_validation_message(
                    source=f"id segment key {value}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"{_quote_texts(not_allowed_chars)} must not be used. The segment key must be a valid hsegment",
                    highlight_pattern = value,
                    highlight_sub = not_allowed_chars
            )

        # Segment key SHOULD be limited to A-Z, 0-9, and -+..
        if not_recommended_chars := set(re.sub(r'[A-Z0-9-:+]', '', key)):
            self._add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"{_quote_texts(not_recommended_chars)} should not be used. Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+' ",
                    highlight_pattern = key,
                    highlight_sub = not_recommended_chars
                )
            
        # Segment key should be in Well know keys
        if key and key not in [k.value for k in WellKnownKeys]:
            self._add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"{key} is not a well known segment key. It is RECOMMENDED to use well-known keys.",
                    highlight_pattern = key,
                    highlight_sub=[key]
                )
            
            
        # Segment value SHOULD be limited to A-Z, 0-9, and -+..
        if not_recommended_chars := set(re.sub(r'[A-Z0-9-:+]', '', value)):
            self._add_validation_message(
                    source=f"id segment value {value}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg=f"Characters {_quote_texts(not_recommended_chars)} should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+' ",
                    highlight_pattern = value,
                    highlight_sub = not_recommended_chars
                )
            
        # Segment value SHOULD be limited to A-Z, 0-9, and :-+ for new designs.
        # this means that ":" in key or value is problematic
        if ':' in key:
            self._add_validation_message(
                    source=f"id segment key {key}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg="Character ':' should not be used in segment key, since this character is used to separate key and value this can lead to undefined behaviour.",
                    highlight_pattern = key
                )
        if ':' in value:
            self._add_validation_message(
                    source=f"id segment value {value}",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    msg="Character ':' should not be used in segment value, since this character is used to separate key and value this can lead to undefined behaviour.",
                    highlight_pattern = value
                )
                
        return self
     
  

class PACID(LabFREED_BaseModel):
    '''Represents a PAC-ID. 
    Refer to the [specification](https://github.com/ApiniLabs/PAC-ID?tab=readme-ov-file#specification) for details.
    '''
    issuer:str 
    '''The issuer of the PAC-ID.'''
    identifier: conlist(IDSegment) = Field(..., default_factory=list) # type: ignore # exclude=True prevents this from being serialized by Pydantic
    '''The identifier of the PAC-ID is a series of IDSegments'''
    
    
    def serialize(self):
        ''' Serializes the PAC-ID'''
        return str(self)
        
        
    @model_validator(mode='after')
    def _check_at_least_one_segment(self) -> Self:
        if not len(self.identifier) >= 1:
            self._add_validation_message(
                        source="identifier",
                        level = ValidationMsgLevel.ERROR,
                        msg=f'Identifier must contain et least one segment.'
                    )
        return self
    
        
    @model_validator(mode='after')
    def _check_length(self) -> Self:
        length = 0
        for s in self.identifier:
            s:IDSegment = s
            if s.key:
                length += len(s.key)
                length += 1 # for ":"
            length += len(s.value)
        length += len(self.identifier) - 1 # account for "/" separating the segments
        
        if length > 256:
            self._add_validation_message(
                        source="identifier",
                        level = ValidationMsgLevel.ERROR,
                        msg=f'Identifier is {length} characters long, Identifier must not exceed 256 characters.'
                    )
        return self
       
    
    @model_validator(mode="after")
    def _validate_issuer(self):
        if not re.fullmatch(_domain_name_pattern, self.issuer):
            self._add_validation_message(
                    source="PAC-ID",
                    level = ValidationMsgLevel.ERROR,
                    highlight_pattern=self.issuer,
                    msg="Issuer must be a valid domain name. "
                )
         
        # recommendation that A-Z, 0-9, -, and . should be used
        if not_recommended_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.issuer)):
            self._add_validation_message(
                    source="PAC-ID",
                    level = ValidationMsgLevel.RECOMMENDATION,
                    highlight_pattern=self.issuer,
                    highlight_sub=not_recommended_chars,
                    msg=f"Characters {' '.join(not_recommended_chars)} should not be used. Issuer SHOULD contain only the characters A-Z, 0-9, -, and . "
                )
        return self
    
    
    @model_validator(mode='after')
    def _check_identifier_segment_keys_are_unique(self) -> Self:
        keys = [s.key for s in self.identifier if s.key]
        duplicate_keys = [k for k in set(keys) if keys.count(k) > 1]
        if duplicate_keys:
            for k in duplicate_keys:
                self._add_validation_message(
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
    
    

    
    



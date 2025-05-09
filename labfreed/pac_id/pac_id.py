import re
from typing_extensions import Self
from pydantic import Field, conlist, model_validator

from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel
from labfreed.pac_id.id_segment import IDSegment
from labfreed.pac_id.extension import Extension


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


_domain_name_pattern = r"(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}"

class PAC_ID(LabFREED_BaseModel):
    '''Represents a PAC-ID. 
    Refer to the [specification](https://github.com/ApiniLabs/PAC-ID?tab=readme-ov-file#specification) for details.
    '''
    issuer:str 
    '''The issuer of the PAC-ID.'''
    identifier: conlist(IDSegment) = Field(..., default_factory=list) # type: ignore # exclude=True prevents this from being serialized by Pydantic
    '''The identifier of the PAC-ID is a series of IDSegments'''
    
    extensions: list[Extension] = Field(default_factory=list)
    
    
    def get_extension_of_type(self, type:str) -> list[Extension]:
        '''Get all extensions of a certain type.'''
        return [e for e in self.extensions if e.type == type]
    
    
    def get_extension(self, name:str) -> Extension|None:
        '''Get extension of certain name'''
        out = [e for e in self.extensions if e.name == name]
        if not out:
            return None
        return out[0]
    
    @classmethod
    def from_url(cls, url, *, extension_interpreters='default', 
                 try_pac_cat=True,
                 suppress_validation_errors=False) -> Self:
        from labfreed.pac_id.url_parser import PAC_Parser
        return PAC_Parser.from_url(url, try_pac_cat=try_pac_cat, suppress_validation_errors=suppress_validation_errors, extension_interpreters=extension_interpreters)
    
    def to_url(self, use_short_notation:None|bool=None, uppercase_only=False) -> str:
        from labfreed.pac_id.url_serializer import PACID_Serializer
        return PACID_Serializer.to_url(self, use_short_notation=use_short_notation, uppercase_only=uppercase_only)
    
    def to_json(self, indent=None) -> str:
        if not indent:
            return self.model_dump_json()
        else:
            return self.model_dump_json(indent=indent)
        
    def to_dict(self) -> dict:
        return self.model_dump()
    
    def __str__(self):
        return self.to_url()
          
         
    @model_validator(mode='after')
    def _check_at_least_one_segment(self) -> Self:
        if not len(self.identifier) >= 1:
            self._add_validation_message(
                        source="identifier",
                        level = ValidationMsgLevel.ERROR,
                        msg='Identifier must contain et least one segment.'
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
    
    

    
    

    
    



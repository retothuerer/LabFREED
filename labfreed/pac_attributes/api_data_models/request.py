import logging
from typing import   Any, Self
from urllib.parse import unquote
from werkzeug.datastructures import LanguageAccept
from pydantic import ConfigDict, field_validator, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, LabFREED_ValidationError, ValidationMsgLevel
from labfreed.pac_id.pac_id import PAC_ID

ATTR_GROUPS = 'attr_grps'
ATTR_GROUPS_FWD_LKP= 'attr_fwd_lkp'


class AttributeRequestData(LabFREED_BaseModel):    
    pac_id: str
    language_preferences: list[str]|None = None
    restrict_to_attribute_groups: list[str]|None = None
    do_forward_lookup: bool = True
    
    def as_json(self):
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json) -> Self:
        return cls.model_validate_json(json)
    
    @classmethod
    def from_http_request(cls, pac_id:str, params:dict, headers:dict):
        restrict_to_attribute_groups = params.get(ATTR_GROUPS)
        if restrict_to_attribute_groups:
            restrict_to_attribute_groups = restrict_to_attribute_groups.split(',')
        do_forward_lookup = params.get(ATTR_GROUPS_FWD_LKP,'true').lower() in ['true', '1']
        language_preferences = headers.get('Accept-Language')
        out = cls(pac_id=pac_id, 
                            restrict_to_attribute_groups = restrict_to_attribute_groups,
                            do_forward_lookup = do_forward_lookup,
                            language_preferences=language_preferences
                            )
        
        return out
        

    
    

    
    @model_validator(mode="before")
    @classmethod
    def _scalars_to_list(cls, d):
        if isinstance(lp:= d.get("language_preferences"), str):
            d["language_preferences"] = [lp]
        if isinstance(rag := d.get("restrict_to_attribute_groups"), str):
            d["restrict_to_attribute_groups"] = [rag]
        return d
    
    
    # @field_validator('language_preferences', mode="before")
    # @classmethod
    # def _convert_language_given_as_language_accept(cls, lp):
    #     v  = [v for v in lp.split(',')]
    #     return v
    
    
    @model_validator(mode="after")
    def _revert_url_encoding(self):
        self.pac_id = unquote(self.pac_id)
        if self.restrict_to_attribute_groups:
            self.restrict_to_attribute_groups = [unquote(g) for g in self.restrict_to_attribute_groups]
        return self
       
    @model_validator(mode="after")
    def _validate_pacs(self) -> Self:           
        try:
            PAC_ID.from_url(self.pac_id)
        except LabFREED_ValidationError:
            self._add_validation_message(
                    source="pac_id",
                    level = ValidationMsgLevel.ERROR,
                    msg='{self.pac_id} is not a valid PAC-ID'
                )
                
        if not self.is_valid:
            raise LabFREED_ValidationError(message='Invalid request', validation_msgs=self.validation_messages())
                
        return self
    
    def language_preference_http_header(self) -> dict[str, str]:
        if not self.language_preferences:
            return {}
        lq = [(lng, 1-i/len(self.language_preferences)) for i, lng in enumerate(self.language_preferences)]
        headers={'Accept-Language':  LanguageAccept(lq).to_header()}
        return headers
    
    def request_params(self) -> dict[str, Any]:
        params = {ATTR_GROUPS_FWD_LKP: self.do_forward_lookup}
        if self.restrict_to_attribute_groups:
            params.update({ATTR_GROUPS: ','.join(self.restrict_to_attribute_groups)})
        return params
        
    
    

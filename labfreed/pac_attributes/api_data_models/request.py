import re
from typing import   Any, Self
from urllib.parse import unquote
from werkzeug.datastructures import LanguageAccept
from werkzeug.http import parse_accept_header
from pydantic import ConfigDict, field_validator, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, LabFREED_ValidationError, ValidationMsgLevel
from labfreed.pac_id.pac_id import PAC_ID

ATTR_GROUPS = 'attr_grps'
ATTR_GROUPS_FWD_LKP= 'attr_fwd_lkp'


class AttributeRequestData(LabFREED_BaseModel):  
    model_config = ConfigDict(arbitrary_types_allowed=True)  
    
    pac_id: str
    language_preferences: LanguageAccept|None = None
    restrict_to_attribute_groups: list[str]|None = None
    do_forward_lookup: bool = True
    
    def as_json(self):
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json) -> Self:
        return cls.model_validate_json(json)
    
    @classmethod
    def from_http_request(cls, pac_id:str, params:dict, headers:dict):
        # Azure seems to meddle with double slashes in a path, even if url encoded. This is to rectify this behaviour and add back a second slash if necessary
        pac_id = re.sub('HTTPS:/{1,2}', 'HTTPS://', pac_id, re.IGNORECASE)
        
        restrict_to_attribute_groups = params.get(ATTR_GROUPS)
        if restrict_to_attribute_groups == '':
            restrict_to_attribute_groups = None
        if restrict_to_attribute_groups:
            restrict_to_attribute_groups = restrict_to_attribute_groups.split(',')
            
        fwd_lkp = params.get(ATTR_GROUPS_FWD_LKP, True)
        if fwd_lkp is True:
            do_forward_lookup = True
        else:
            do_fwd_lookup =  fwd_lkp.lower() not in ['false', 'no', '0', 'n', 'off']

        lang_hdr = headers.get('Accept-Language')
        language_preferences: LanguageAccept = parse_accept_header(lang_hdr, LanguageAccept)
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
    
    
    @field_validator('language_preferences', mode='before')
    @classmethod
    def convert_language_preferences(cls,lp):
        if isinstance(lp, LanguageAccept):
            return lp
        lq = [(lng, 1-i/len(lp)) for i, lng in enumerate(lp)]
        return LanguageAccept(lq)
        
    
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
                    msg=f'{self.pac_id} is not a valid PAC-ID'
                )
                
        if not self.is_valid:
            raise LabFREED_ValidationError(message='Invalid request', validation_msgs=self.validation_messages())
                
        return self
    
    def language_preference_http_header(self) -> dict[str, str]:
        if not self.language_preferences:
            return {}
        headers={'Accept-Language':  LanguageAccept(self.language_preferences).to_header()}
        return headers
    
    def request_params(self) -> dict[str, Any]:
        params = {ATTR_GROUPS_FWD_LKP: self.do_forward_lookup}
        if self.restrict_to_attribute_groups:
            params.update({ATTR_GROUPS: ','.join(self.restrict_to_attribute_groups)})
        return params
        
    
    

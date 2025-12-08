import logging
from typing import   Self
from urllib.parse import unquote
from werkzeug.datastructures import LanguageAccept
from pydantic import ConfigDict, field_validator, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, LabFREED_ValidationError, ValidationMsgLevel
from labfreed.pac_id.pac_id import PAC_ID


class AttributeRequestData(LabFREED_BaseModel):
    model_config = ConfigDict(frozen=True)
    
    pac_id: str
    language_preferences: list[str]|None = None
    restrict_to_attribute_groups: list[str]|None = None
    suppress_forward_lookup: bool = False
    
    def as_json(self):
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json):
        return cls.model_validate_json(json)
    
    @classmethod
    @model_validator(mode="before")
    def _scalars_to_list(cls, d):
        if isinstance(lp:= d.get("language_preferences"), str):
            d["language_preferences"] = [lp]
        if isinstance(rag := d.get("restrict_to_attribute_groups"), str):
            d["restrict_to_attribute_groups"] = [rag]
        return d
    
    @classmethod
    @field_validator('language_preferences', mode="before")
    def _convert_language_given_as_language_accept(cls, lp):
        if isinstance(lp, LanguageAccept):
            v  = [v[0] for v in lp.values()]
        return v
    
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
        lq = [(lng, 1-i/len(self.language_preferences)) for i, lng in enumerate(self.language_preferences)]
        headers={'Accept-Language':  LanguageAccept(lq).to_header()}
        return headers
    
    def request_params(self) -> dict(str, Any):
        
    
    

import logging
from typing import   Self
from flask import redirect
from pydantic import ConfigDict, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, LabFREED_ValidationError, ValidationMsgLevel
from labfreed.pac_id.pac_id import PAC_ID


class AttributeRequestData(LabFREED_BaseModel):
    model_config = ConfigDict(frozen=True)
    
    pac_id: str
    language_preferences: list[str]|str|None = None
    restrict_to_attribute_groups: list[str]|str|None = None
    suppress_forward_lookup: bool = False
    
    def as_json(self):
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json):
        return cls.model_validate_json(json)
    
    @model_validator(mode="before")
    @classmethod
    def _handle_multiple_pac_url(cls, data):
        p = data.get('pac_id')
        if isinstance(p, list) and len(p) > 0:
            logging.error("Multiple PAC-ID are no longer supported. For half assed backwards compatibility the first element is now selected.")
            data['pac_id'] = p[0]
        return data
    
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
    
    
    


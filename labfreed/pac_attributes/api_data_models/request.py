from typing import   Self
from pydantic import ConfigDict, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, LabFREED_ValidationError, ValidationMsgLevel
from labfreed.pac_id.pac_id import PAC_ID


class AttributeRequestPayload(LabFREED_BaseModel):
    model_config = ConfigDict(frozen=True)
    
    pac_urls: list[str]
    restrict_to_attribute_groups: list[str]|None = None
    suppress_translations: bool = False
    suppress_forward_lookup: bool = False
    
    def as_json(self):
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json):
        return cls.model_validate_json(json)
    
    @model_validator(mode="before")
    @classmethod
    def _handle_single_pac_url(cls, data):
        p = data.get('pac_urls')
        if isinstance(p, str):
            data['pac_urls'] = [p]
        return data
    
    @model_validator(mode="after")
    def _validate_pacs(self) -> Self:
        if len(self.pac_urls) > 100:
            self._add_validation_message(
                        source="pacs",
                        level = ValidationMsgLevel.ERROR,
                        msg='The number of pac-ids must be limited to 100'
                    )
            
        for pac_url in self.pac_urls:
            try:
                PAC_ID.from_url(pac_url)
            except LabFREED_ValidationError:
                self._add_validation_message(
                        source="pacs",
                        level = ValidationMsgLevel.ERROR,
                        msg='{pac_url} is not a valid PAC-ID'
                    )
                
        if not self.is_valid:
            raise LabFREED_ValidationError(message='Invalid request', validation_msgs=self.validation_messages())
                
        return self
    
    
    


from typing import Annotated, Any, Iterable, List
from pydantic import ConfigDict, field_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_attributes.api_data_models.request import AttributeRequestPayload
from labfreed.pac_id.pac_id import PAC_ID


class pyAttributeRequestPayload(LabFREED_BaseModel):
    model_config = ConfigDict(frozen=True)
    
    pac_ids: Annotated[List[PAC_ID], "Accepts PAC_IDs in urls form or PAC_ID instances"]
    include_translations: bool = False
    
    
    @field_validator("pac_ids")
    def validate_pac_ids(v:Any):
        if not isinstance(v, Iterable):
            v = [v]
        return [ PAC_ID.from_url(p) if isinstance(p, str) else p for p in v ]
    
    def to_payload(self, include_extensions=False):
        pac_urls = [p.to_url(include_extensions=include_extensions) for p in self.pac_ids]
        return AttributeRequestPayload(pac_urls=pac_urls)
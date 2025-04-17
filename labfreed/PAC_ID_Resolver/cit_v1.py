
from enum import Enum
from labfreed.labfreed_infrastructure import LabFREED_BaseModel

class ServiceType(Enum):
    USER_HANDOVER_GENERIC = 'userhandover-generic'
    ATTRIBUTE_SERVICE_GENERIC = 'attributes-generic'


class CITEntry_v1(LabFREED_BaseModel):
    applicable_if: str
    service_name: str
    application_intents:list[str]
    service_type:ServiceType
    template_url:str

class CIT_v1(LabFREED_BaseModel):
    origin:str = ''
    entries:list[CITEntry_v1]


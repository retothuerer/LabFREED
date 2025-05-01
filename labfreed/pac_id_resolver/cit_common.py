from enum import Enum
import re
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel, _quote_texts



class ServiceType(Enum):
    USER_HANDOVER_GENERIC = 'userhandover-generic'
    ATTRIBUTE_SERVICE_GENERIC = 'attributes-generic'


def _validate_service_name(service_name):
    msg_dict = []
    if not_allowed_chars := set(re.sub(r'[A-Za-z0-9\-\x20]', '', service_name)):
        msg_dict.append( {
                "level": ValidationMsgLevel.ERROR,
                "msg": f'Service name ontains invalid characters {_quote_texts(not_allowed_chars)}',
                "highlight_sub": not_allowed_chars
            }
        )
    
    if len(service_name) == 0 or len(service_name) > 255:
        msg_dict.append( {
                "level": ValidationMsgLevel.ERROR,
                "msg": 'Service name must be at least one and maximum 255 characters long'
            }
        )
    return msg_dict
        
    
def _validate_application_intent(intent):
    msg_dict = []
    if re.fullmatch('.*-generic$',  intent):
        msg_dict.append( {
                "level": ValidationMsgLevel.ERROR,
                "msg": "Application intent ends with '-generic'. This is not permitted, since it is reserved for future uses'",
                "highlight_sub": [intent]
            }
        )

    if not_allowed_chars := set(re.sub(r'[A-Za-z0-9\-]', '', intent)):
        msg_dict.append( {
                "level": ValidationMsgLevel.ERROR,
                "msg": f'Application intent contains invalid characters {_quote_texts(not_allowed_chars)}',
                "highlight_sub": not_allowed_chars
            }
        )
        
    if len(intent) == 0 or len(intent) > 255:
        msg_dict.append( {
                "level": ValidationMsgLevel.ERROR,
                "source": f'Application intent  {intent}',
                "msg": 'Must be at least one and maximum 255 characters long'
            }
        )
    return msg_dict

    
def _validate_service_type(service_type):
    msg_dict = []
    if isinstance(service_type, ServiceType):
            service_type= service_type.value
    else:
        service_type= service_type
    allowed_types = [ServiceType.ATTRIBUTE_SERVICE_GENERIC.value, ServiceType.USER_HANDOVER_GENERIC.value]
    if service_type not in allowed_types:
        msg_dict.append( {
                "level": ValidationMsgLevel.ERROR,
                "msg": f'Invalid service type. Must be {_quote_texts(allowed_types)} must be at least one and maximum 255 characters long',
                "highlight_sub": service_type
            }
        )
    return msg_dict


def _add_msg_to_cit_entry_model(msg_dict, model):
    for m in msg_dict:
        m.update({"source": model.service_name})
        model._add_validation_message(**m)
    return model
    
   


from datetime import UTC, datetime, timedelta


from labfreed.pac_attributes.api_data_models.response import AttributeGroup
from labfreed.pac_id.pac_id import PAC_ID



class ClientAttributeGroup(AttributeGroup):
    ''' extends attribute group with info the client needs'''
    origin:str
    language:str
    value_from: datetime | None = None  
    



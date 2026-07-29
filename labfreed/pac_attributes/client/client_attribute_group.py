

from labfreed.pac_attributes.api_data_models.response import AttributeGroup


class ClientAttributeGroup(AttributeGroup):
    ''' extends attribute group with info the client needs'''
    origin:str
    language:str    



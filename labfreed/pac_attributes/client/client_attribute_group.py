

from labfreed.pac_attributes.api_data_models.response import Spec_AttributeGroup


class ClientAttributeGroup(Spec_AttributeGroup):
    ''' extends attribute group with info the client needs'''
    origin:str
    language:str    



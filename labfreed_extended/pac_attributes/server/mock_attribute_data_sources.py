from random import choices
import string
from labfreed.pac_attributes.api_data_models.response import AttributeGroup
from labfreed.pac_attributes.python_convenience.py_attributes import pyAttribute, pyAttributes
from labfreed.pac_attributes.server.server import AttributeGroupDataSource
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID


class RandomAttributeGroupDataSource(AttributeGroupDataSource):
    '''
    generates random attributes
    '''
    def __init__(self, attribute_keys:list[str], *args, **kwargs):
        self._attribute_keys = attribute_keys
        super().__init__(*args, **kwargs)

        
    def is_static(self) -> bool:
        return False
    
    def attributes(self, pac_url: str) -> AttributeGroup:
        keys = choices(self._attribute_keys, k=min(3, len(self._attribute_keys)))
        attributes = []
        for k in keys:
            v = ''.join(choices(string.ascii_letters + string.digits, k=10))
            attributes.append(pyAttribute(key=k, value=v))
            
        return AttributeGroup(key=self._attribute_group_key, ontology=self._ontology, attributes=pyAttributes(attributes).to_payload_attributes())
    
    
class PACAnalyzerAttributeDataSource(AttributeGroupDataSource):
    '''
    Demonstrates how to analyze the PAC-ID and it's extensions to provide some data
    '''
        
    def is_static(self) -> bool:
        return False
    
    def attributes(self, pac_url: str) -> AttributeGroup:
        pac = PAC_ID.from_url(pac_url)
        attributes = []
        if isinstance(pac, PAC_CAT):
            attributes.append(pyAttribute(key='IsPAC-CAT', value="This PAC-ID follows the PAC-CAT spezifications."))
            attributes.append(pyAttribute(key='Category', value=f"{pac.categories[0].__class__.__name__}"))
        if pac.get_extension_of_type('TREX'):
            attributes.append(pyAttribute(key='TREX', value="This PAC-ID has a TREX attached."))
            
        return AttributeGroup(key=self._attribute_group_key, attributes=pyAttributes(attributes).to_payload_attributes())
            
            
        
    
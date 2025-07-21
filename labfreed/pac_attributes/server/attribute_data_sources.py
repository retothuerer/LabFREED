    
from random import choice, choices
import string
from labfreed.pac_attributes.api_data_models.response import AttributeGroup
from labfreed.pac_attributes.python_convenience import  pyAttribute, pyAttributes
from labfreed.pac_attributes.server.server import AttributeGroupDataSource
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID


# class StaticAttributeGroupSource(AttributeGroupDataSource):
    
#     def is_static(self) -> bool:
#         return True
    
#     def attributes(self, pac_url: str) -> AttributeGroup:
#         attributes = self._data.get(pac_url)
#         if not attributes:
#             return None
#         return AttributeGroup(key=self._attribute_group_key, attributes=attributes)
    
    
""" class JsonFile_DataSource(AttributeGroupDataSource):
    def __init__(self, attribute_group_key:str, json_file_path:Path):
        with open(json_file_path) as f:
            self._data = json.load(f) """
            

class Dict_DataSource(AttributeGroupDataSource):
    def __init__(self, attribute_group_key:str, data:dict[str, pyAttributes]):
        if not all([isinstance(e, pyAttributes) for e in data.values()]):
            raise ValueError('Invalid data')
        self._data:pyAttributes = data
        
        self._attribute_group_key = attribute_group_key
        
    def is_static(self) -> bool:
        return False
    
        
    def attributes(self, pac_url: str) -> AttributeGroup:
        attributes = self._data.get(pac_url)
        if not attributes:
            return None
        attributes = attributes.to_payload_attributes()

        return AttributeGroup(key=self._attribute_group_key, attributes=attributes)
    
    
    
class RandomAttributeGroupDataSource(AttributeGroupDataSource):
    '''
    generates random attributes
    '''
    def __init__(self, attribute_group_key:str, attribute_keys:list[str]):
        self._attribute_group_key = attribute_group_key
        self._attribute_keys = attribute_keys
        
    def is_static(self) -> bool:
        return False
    
    def attributes(self, pac_url: str) -> AttributeGroup:
        keys = choices(self._attribute_keys, k=min(3, len(self._attribute_keys)))
        attributes = []
        for k in keys:
            v = ''.join(choices(string.ascii_letters + string.digits, k=10))
            attributes.append(pyAttribute(key=k, value=v))
            
        return AttributeGroup(key=self._attribute_group_key, attributes=pyAttributes(attributes).to_payload_attributes())
    
    
class PACAnalyzerAttributeDataSource(AttributeGroupDataSource):
    '''
    Demonstrates how to analyze the PAC-ID and it's extensions to provide some data
    '''
    def __init__(self, attribute_group_key:str):
        self._attribute_group_key = attribute_group_key
        
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
            
            
        
    
    

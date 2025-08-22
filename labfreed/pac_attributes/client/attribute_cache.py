

from datetime import datetime, timedelta
from typing import Literal, Protocol


from labfreed.pac_attributes.api_data_models.response import AttributeGroup
from labfreed.pac_id.pac_id import PAC_ID



class CacheableAttributeGroup(AttributeGroup):
    origin:str
    language:str
    value_from: datetime | None = None  
    
    def still_valid(self, accept_cache_for_minutes):
        if self.value_from is None:
            return False
        else:
            return ( datetime.now() - timedelta(min=accept_cache_for_minutes)) > self.value_from 






class AttributeCache(Protocol):
    def get_all(self, service_url:str, pac:PAC_ID) -> list[CacheableAttributeGroup]:
        pass
    
    def get_attribute_groups(self, service_url:str, pac:PAC_ID, attribute_groups:list[str]):
        pass
        
    def update(self, service_url:str, pac:PAC_ID, attribute_groups:list[CacheableAttributeGroup]):
        pass
    

            
class MemoryAttributeCache(AttributeCache):
    '''simple in-memory implementation of AttributeCache'''
    def __init__(self):
        self._store = dict()
    
    def get_all(self, service_url:str, pac:PAC_ID|str) -> list[CacheableAttributeGroup]:
        if isinstance(pac, str):
            pac = PAC_ID.from_url(pac)
        k = self._generate_dict_key(service_url=service_url, pac=pac)
        
        ags = [CacheableAttributeGroup.model_validate(e) for e in self._store.get(k, [])]
        return ags
    
    def get_attribute_groups(self, service_url:str, pac:PAC_ID, attribute_groups:list[str]):
        all_ags = self.get_all(service_url=service_url, pac=pac)
        selected_ags = [ag for ag in all_ags if ag.key in attribute_groups]
        return selected_ags
        
    def update(self, service_url:str, pac:PAC_ID, attribute_groups: list[CacheableAttributeGroup] ):
        k = self._generate_dict_key(service_url=service_url, pac=pac)
        self._store.update({k: [e.model_dump() for e in attribute_groups]})
    
    @staticmethod
    def _generate_dict_key(service_url:str, pac:PAC_ID):
        key = service_url +";"+ pac.to_url(include_extensions=False) 
        return key
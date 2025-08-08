from abc import ABC, abstractmethod, abstractproperty
from datetime import datetime, timezone
from labfreed.pac_attributes.api_data_models.response import VALID_FOREVER, AttributeBase, AttributeGroup


class AttributeGroupDataSource(ABC):
    
    def __init__(self, attribute_group_key:str, include_extensions:bool=False, is_static:bool=False, ):
        self._attribute_group_key = attribute_group_key
        self._include_extensions = include_extensions
        self._is_static = is_static
       
    @property
    def is_static(self) -> bool:
        return self._is_static
    
    
    @property
    def attribute_group_key(self):
        return self._attribute_group_key
    
    @abstractproperty
    def provides_attributes(self):
        pass
    
    @abstractmethod
    def attributes(self, pac_url: str) -> AttributeGroup:
        pass
    

class Dict_DataSource(AttributeGroupDataSource):
    def __init__(self, data:dict[str, list[AttributeBase]], *args, **kwargs):
        if not all([isinstance(e, list) for e in data.values()]):
            raise ValueError('Invalid data')
        
        self._data = data
        self._state_of = datetime.now(tz=timezone.utc)
        
        super().__init__(*args, **kwargs)       
        
    
    @property
    def provides_attributes(self):
        return [a.key for attributes in self._data.values() for a in attributes]
    
           
    def attributes(self, pac_url: str) -> AttributeGroup:
        if not self._include_extensions:
            pac_url = pac_url.split('*')[0]
        
        attributes = self._data.get(pac_url)
        if not attributes:
            return None     
        
        
        valid_until = VALID_FOREVER if self._is_static else None
        

        return AttributeGroup(key=self._attribute_group_key, 
                              attributes=attributes, 
                              state_of=self._state_of, 
                              valid_until=valid_until)
        
        
        

    
    

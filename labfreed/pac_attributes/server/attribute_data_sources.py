from abc import ABC, abstractmethod, abstractproperty
from datetime import datetime, timezone
from labfreed.pac_attributes.api_data_models.response import AttributeBase, AttributeGroup
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID


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
    def __init__(self, data:dict[str, list[AttributeBase]], uses_pac_cat_short_form=True, pac_to_key: callable = None, *args, **kwargs):
        if not all([isinstance(e, list) for e in data.values()]):
            raise ValueError('Invalid data')
        
        self._data = data
        self.uses_pac_cat_short_form = uses_pac_cat_short_form
        self._pac_to_key = pac_to_key
        
        super().__init__(*args, **kwargs)       
        
    
    @property
    def provides_attributes(self):
        return [a.key for attributes in self._data.values() for a in attributes]
    
           
    def attributes(self, pac_url: str) -> AttributeGroup:
        try:
            p = PAC_CAT.from_url(pac_url)
            pac_url = p.to_url(use_short_notation=self.uses_pac_cat_short_form, include_extensions=self._include_extensions)
        except:
            ... # might as well try to match the original input
            
        
        lookup_key = self._pac_to_key(pac_url) if self._pac_to_key else pac_url
        attributes = self._data.get(lookup_key)
        if not attributes:
            if 'default' in self._data.keys():
                attributes = self._data.get('default', None)
            else:
                return None  
        
        return AttributeGroup(key=self._attribute_group_key, 
                              attributes=attributes)
        
        
        

    
    

from abc import ABC, abstractmethod, abstractproperty
from labfreed.pac_attributes.api_data_models.response import DEFAULT_ONTOLOGY_KEY, AttributeGroup
from labfreed.pac_attributes.python_convenience.py_attributes import pyAttributes


class AttributeGroupDataSource(ABC):
    
    def __init__(self, attribute_group_key:str, ontology:str=DEFAULT_ONTOLOGY_KEY, include_extensions:bool=False):
        self._attribute_group_key = attribute_group_key
        self._ontology = ontology
        self._include_extensions = include_extensions
       
    @abstractproperty
    def is_static(self) -> bool:
        pass
    
    @property
    def attribute_group_key(self):
        return self._attribute_group_key
    
    @abstractmethod
    def attributes(self, pac_url: str) -> AttributeGroup:
        pass
    

class Dict_DataSource(AttributeGroupDataSource):
    def __init__(self, data:dict[str, pyAttributes], *args, **kwargs):
        if not all([isinstance(e, pyAttributes) for e in data.values()]):
            raise ValueError('Invalid data')
        self._data:pyAttributes = data
        
        super().__init__(*args, **kwargs)

        
    def is_static(self) -> bool:
        return False
           
    def attributes(self, pac_url: str) -> AttributeGroup:
        if not self._include_extensions:
            pac_url = pac_url.split('*')[0]
        
        attributes:pyAttributes = self._data.get(pac_url)
        if not attributes:
            return None
        attributes = attributes.to_payload_attributes()
        

        return AttributeGroup(key=self._attribute_group_key, attributes=attributes, ontology=self._ontology)
    
    
    

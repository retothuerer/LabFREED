from abc import ABC, abstractmethod, abstractproperty
from labfreed.pac_attributes.api_data_models.response import DEFAULT_ONTOLOGY_KEY, AttributeGroup
from labfreed.pac_attributes.python_convenience.py_attributes import pyAttributes
from labfreed.pac_id.pac_id import PAC_ID


class AttributeGroupDataSource(ABC):
    
    def __init__(self, attribute_group_key:str, ontology:str=DEFAULT_ONTOLOGY_KEY):
        self._attribute_group_key = attribute_group_key
        self._ontology = ontology
       
    @abstractproperty
    def is_static(self) -> bool:
        pass
    
    @property
    def attribute_group_key(self):
        return self._attribute_group_key
    
    @abstractmethod
    def attributes(self, pac_id: PAC_ID) -> AttributeGroup:
        pass
    

class Dict_DataSource(AttributeGroupDataSource):
    def __init__(self, attribute_group_key:str, data:dict[str, pyAttributes], onthology:str='default'):
        if not all([isinstance(e, pyAttributes) for e in data.values()]):
            raise ValueError('Invalid data')
        self._data:pyAttributes = data
        
        super().__init__(attribute_group_key=attribute_group_key, ontology=onthology)

        
    def is_static(self) -> bool:
        return False
           
    def attributes(self, pac_url: str) -> AttributeGroup:
        attributes:pyAttributes = self._data.get(pac_url)
        if not attributes:
            return None
        attributes = attributes.to_payload_attributes()
        

        return AttributeGroup(key=self._attribute_group_key, attributes=attributes, ontology=self._ontology)
    
    
    

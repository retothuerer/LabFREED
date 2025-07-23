from abc import ABC, abstractmethod, abstractproperty
from datetime import datetime, timezone

from labfreed.pac_attributes.api_data_models.request import AttributeRequestPayload
from labfreed.pac_attributes.api_data_models.response import AttributeGroup, AttributeResponsePayload,  AttributesOfPACID, DateTimeValue, ReferenceAttribute, Translations
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.trex.python_convenience.pyTREX import _date_value_from_python_type



class AttributeGroupDataSource(ABC):
    
    def __init__(self, attribute_group_key:str):
        self._attribute_group_key = attribute_group_key
       
    @abstractproperty
    def is_static(self) -> bool:
        pass
    
    @abstractmethod
    def attributes(self, pac_id: PAC_ID) -> AttributeGroup:
        pass
       
    
class TranslationDataSource(ABC):
    @abstractmethod
    def get(key:str) -> list[Translations]:
        pass
    
    

class InvalidRequestError(ValueError):
    pass


    
class AttributeServerRequestHandler():
    def __init__(self, data_sources:list[AttributeGroupDataSource], translation_data_source:TranslationDataSource):
        if isinstance(data_sources, AttributeGroupDataSource):
            data_sources = [data_sources]
        self._attribute_group_data_sources: list[AttributeGroupDataSource] = data_sources
        
        self._translation_data_source = translation_data_source
               
        
    def handle_attribute_request(self, json_request_body:str) -> str:
        try:
            r = AttributeRequestPayload.model_validate_json(json_request_body)
        except:
            raise InvalidRequestError
        response_timestamp = datetime.now(tz=timezone.utc) # UTC !!
        attributes_for_pac_id = []
        translations=None
        referenced_pac_ids = []
        for pac_url in r.pac_urls:
            attributes_for_pac = self.get_attributes_for_pac_id(pac_url=pac_url, response_timestamp=response_timestamp)
            attributes_for_pac_id.append(attributes_for_pac)
            ref = self.get_referenced_pac_ids(attributes_for_pac)
            if ref:
                referenced_pac_ids.extend(ref)
            
        # also find attributes of referenced pac-ids 
        for pac_url in referenced_pac_ids:
            attributes_for_pac = self.get_attributes_for_pac_id(pac_url=pac_url, response_timestamp=response_timestamp)
            attributes_for_pac_id.append(attributes_for_pac)
            
        # attach relevant display names (fro attribute groups and attributes)
        if not r.suppress_translations:
            translations = []
            attribute_group_keys = [ag.key for ag_for_pac in attributes_for_pac_id for ag in ag_for_pac.attribute_groups]
            attribute_keys = [a.key for ag_for_pac in attributes_for_pac_id for ag in ag_for_pac.attribute_groups for a in ag.attributes]
            for k in set(attribute_group_keys + attribute_keys):
                t = self._translation_data_source.get(k)
                if t:
                    translations.append(t)
            
        response = AttributeResponsePayload(pac_attributes=attributes_for_pac_id, translations=translations).to_json()
        return response
    

    def get_attributes_for_pac_id(self, pac_url:str, response_timestamp:datetime ):
        attribute_groups = []
        for ds in self._attribute_group_data_sources:
            ag = ds.attributes(pac_url)
            if ag:
                attribute_groups.append(ag)
                        
        return AttributesOfPACID(pac_url=pac_url, # return the pac_url as given, i.e. with the extension if there was one
                                 response_from=response_timestamp, 
                                 attribute_groups=attribute_groups)
            
    
    
    def get_referenced_pac_ids(self, attributes_for_pac:AttributesOfPACID):
        referenced_pacs = []
        for ag in attributes_for_pac.attribute_groups:
            for a in ag.attributes :
                if isinstance(a, ReferenceAttribute):
                    try:
                        PAC_ID.from_url(a.value)
                        referenced_pacs.append(a.value)
                    except:
                        pass
        return referenced_pacs
            
            
            







    
        
        
        
    

    
    
    
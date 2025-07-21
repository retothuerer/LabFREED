from __future__ import annotations

from abc import ABC
from datetime import datetime
from functools import cache, cached_property
from typing import Any, Dict, Literal, Optional, Protocol
from typing import Callable, Optional, Dict, Any


from pydantic import BaseModel, computed_field, model_validator
import requests

from labfreed.pac_attributes.api_data_models.request import AttributeRequestPayload
from labfreed.pac_attributes.api_data_models.response import AttributeGroup, AttributeResponsePayload, Translations
from labfreed.pac_id.pac_id import PAC_ID

        
        
class AttributeCache(Protocol):
    def get_all(self, service_url:str, pac:PAC_ID) -> list[CacheableAttributeGroup]:
        pass
        
    def update(self, service_url:str, pac:PAC_ID, attribute_groups:list[CacheableAttributeGroup]):
        pass
    

            
    
class MemoryCache(AttributeCache, dict):
    def __init__(self):
        self._store = dict()
    
    def get_all(self, service_url:str, pac:PAC_ID|str) -> list[CacheableAttributeGroup]:
        if isinstance(pac, str):
            pac = PAC_ID.from_url(pac)
        k = self._generate_dict_key(service_url=service_url, pac=pac)
        
        ag = [CacheableAttributeGroup.model_validate(e) for e in self._store.get(k, [])]
        return ag
        
    def update(self, service_url:str, pac:PAC_ID, attribute_groups: list[CacheableAttributeGroup] ):
        k = self._generate_dict_key(service_url=service_url, pac=pac)
        self._store.update({k: [e.model_dump() for e in attribute_groups]})
    
    @staticmethod
    def _generate_dict_key(service_url:str, pac:PAC_ID):
        key = service_url +";"+ pac.to_url(include_extensions=False) 
        return key
    
    
    
 
 
    
class TranslationCache(Protocol):
    def get(self, service_url:str, key:str) -> Translations:
        pass
        
    def update(self, service_url:str, translations:Translations):
        pass
    

            
    
class TranslationMemoryCache(AttributeCache, dict):
    def __init__(self):
        self._store = dict()
    
    def get(self, service_url:str, key:str) -> Translations:
        k = self._generate_dict_key(service_url=service_url, key=key)
        
        t = [Translations.model_validate(e) for e in self._store.get(k, [])]
        return t
        
    def update(self, service_url:str, translations:Translations|list[Translations]):
        if not isinstance(translations, list):
            translations = [translations]
            
        for t in translations:
            k = self._generate_dict_key(service_url=service_url, key=t.key)
            self._store.update({k: t.model_dump()})
    
    @staticmethod
    def _generate_dict_key(service_url:str, key:str):
        key = service_url +";"+ key
        return key
   
    
    


class AttributeRequestCallback(Protocol):
    def __call__(self, url: str, attribute_request_body: str, params: Optional[dict] = None) -> str:
        ...

    
class AttributeClient():
    '''
    @cache_store: allows to inject the store for the cache. If non is given an im memory cache is used.
    @http_get_callback: allows to inject a http client. This is done to delegate authentication to the application using the library. If non is given, pythons requests module is used.
    '''
    def __init__(self, http_get_callback:AttributeRequestCallback|None=None, cache_store:AttributeCache|None=None, translation_cache_store:TranslationCache|None=None):
        if cache_store:
            self.cache = cache_store
        else:
            self.cache = MemoryCache()
            
        if translation_cache_store:
            self.translations_cache = translation_cache_store
        else:
            self.translations_cache = TranslationMemoryCache()
            
        if http_get_callback:
            self.http_get_callback = http_get_callback
        else: 
            def default_callback(url:str, attribute_request_body=str, params:dict=None) -> str:
                response = requests.get(url=url, data=attribute_request_body, headers={'Content-Type': 'application/json'})
                if not response.ok:
                    pass 
                return response.text
            self.http_get_callback = default_callback
            
    
    def get_attributes(self, server_url:str, pac_id:PAC_ID|str) -> list[CacheableAttributeGroup]:
        if isinstance(pac_id, str):
            pac_id = PAC_ID.from_url(pac_id)
        
        # try the cache
        attribute_groups = self.cache.get_all(server_url, pac_id)
        if attribute_groups and all([ag.still_valid for ag in attribute_groups]): 
            return attribute_groups
        
        else: # no valid data found in cache > request to server
            attribute_request_body = AttributeRequestPayload(pac_urls=[pac_id.to_url(include_extensions=False)])
            response_json = self.http_get_callback(server_url, attribute_request_body.model_dump_json())
            r = AttributeResponsePayload.model_validate_json(response_json)
            
            # update translations cache
            if r.translations:
                self.translations_cache.update(service_url=server_url, translations=r.translations)
            
            # update cache
            for ag_for_pac in r.responses:
                pac = PAC_ID.from_url(ag_for_pac.pac_url)
                ags = [CacheableAttributeGroup(key= ag.key, attributes=ag.attributes, origin=server_url) for ag in ag_for_pac.attribute_groups]
                self.cache.update(server_url, pac, ags)
                
                if pac_id == pac:
                    attribute_groups_out = ags
            return attribute_groups_out
            
                
    
                
    



class CacheableAttributeGroup(AttributeGroup):
    origin:str
    valid_until: Literal['forever'] | datetime | None = None
    
    @model_validator(mode='after')
    def set_valid_until(self) -> 'CacheableAttributeGroup':
        vals = [a.valid_until for a in self.attributes]
        if all(e == 'forever' for e in vals):
            self.valid_until = 'forever'
        elif any(e is None for e in vals):
            self.valid_until = None
        else:
            self.valid_until = min(v for v in vals if isinstance(v, datetime))
        return self
    
    
    @property
    def still_valid(self):
        if self.valid_until is None:
            return False
        if self.valid_until == 'forever':
            return True
        
        return self.valid_until > datetime.now()




from __future__ import annotations

from dataclasses import dataclass
from typing import   Any, Optional, Protocol, runtime_checkable

import urllib.request
import urllib.error

from pydantic import BaseModel, ConfigDict

from labfreed.pac_attributes.api_data_models.request import AttributeRequestPayload
from labfreed.pac_attributes.api_data_models.response import DEFAULT_ONTOLOGY_KEY,  AttributeResponsePayload
from labfreed.pac_attributes.client.translation_cache import TranslationCache, TranslationMemoryCache
from labfreed.pac_attributes.client.attribute_cache import AttributeCache, CacheableAttributeGroup, MemoryAttributeCache
from labfreed.pac_id.pac_id import PAC_ID

        



@runtime_checkable
class AttributeRequestCallback(Protocol):
    def __call__(self, url: str, attribute_request_body: str, params: Optional[dict] = None) -> str:
        ...



class AttributeClientDefaultFactory():
    @staticmethod
    def create_attribute_client():
        cache = MemoryAttributeCache()
            
        translations_cache = TranslationMemoryCache()
            

        def default_callback(url: str, attribute_request_body: str, params: dict = None) -> str:
            req = urllib.request.Request(
                url=url,
                data=attribute_request_body.encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            try:
                with urllib.request.urlopen(req) as response:
                    return response.read().decode('utf-8')
            except urllib.error.HTTPError as e:
                # Optional: log or re-raise error
                return e.read().decode('utf-8')  # or raise
        http_get_callback = default_callback
        
        return AttributeClient(http_get_callback=http_get_callback,
                               cache_store=cache,
                               translation_cache_store=translations_cache)
        
    
@dataclass
class AttributeClient():
    '''
    @cache_store: allows to inject the store for the cache. If non is given an im memory cache is used.
    @http_get_callback: allows to inject a http client. This is done to delegate authentication to the application using the library. If non is given, pythons requests module is used.
    '''
    http_get_callback:AttributeRequestCallback
    cache_store:AttributeCache
    translation_cache_store:TranslationCache
                
    
    def get_attributes(self, server_url:str, pac_id:PAC_ID|str) -> list[CacheableAttributeGroup]:
        if isinstance(pac_id, str):
            pac_id = PAC_ID.from_url(pac_id)
        
        # try the cache
        attribute_groups = self.cache_store.get_all(server_url, pac_id)
        if attribute_groups and all([ag.still_valid for ag in attribute_groups]): 
            return attribute_groups
        
        else: # no valid data found in cache > request to server
            attribute_request_body = AttributeRequestPayload(pac_urls=[pac_id.to_url()])
            response_json = self.http_get_callback(server_url, attribute_request_body.model_dump_json())
            r = AttributeResponsePayload.model_validate_json(response_json)
            
            # update translations cache
            if r.translations_by_ontology:
                for ot in r.translations_by_ontology:
                    if ot.ontology == DEFAULT_ONTOLOGY_KEY:
                        ontology = f"{server_url}/{ot.ontology}"
                    else:
                        ontology = ot.ontology
                    terms = ot.terms
                    self.translation_cache_store.update(ontology=ontology, translations=terms)
            
            # update cache
            for ag_for_pac in r.pac_attributes:
                pac = PAC_ID.from_url(ag_for_pac.pac_url)
                ags = [CacheableAttributeGroup(key= ag.key, attributes=ag.attributes, origin=server_url) for ag in ag_for_pac.attribute_groups]
                self.cache_store.update(server_url, pac, ags)
                
                if pac_id == pac:
                    attribute_groups_out = ags
            return attribute_groups_out
            
                
    



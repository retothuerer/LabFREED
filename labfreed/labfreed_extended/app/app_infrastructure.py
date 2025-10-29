
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo
from labfreed.pac_attributes.client.attribute_cache import MemoryAttributeCache
from labfreed.pac_attributes.client.client import AttributeClient, http_attribute_request_default_callback_factory
from labfreed.pac_attributes.pythonic.py_attributes import pyAttributeGroup

from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.resolver import PAC_ID_Resolver, cit_from_str
from labfreed.pac_id_resolver.services import ServiceGroup

        



class Labfreed_App_Infrastructure():
    def __init__(self, markup = 'rich', language_preferences:list[str]|str='en', http_client:requests.Session|None=None, use_issuer_resolver_config=True):
        if isinstance(language_preferences, str):
            language_preferences = [language_preferences]
        self._language_preferences = language_preferences
        self._use_issuer_resolver_config = use_issuer_resolver_config
        
        self._resolver = PAC_ID_Resolver()
        
        if not http_client:
            http_client = requests.Session()
        self._http_client= http_client
        callback = http_attribute_request_default_callback_factory(http_client)
            
        self._attribute_client = AttributeClient(http_post_callback=callback, cache_store=MemoryAttributeCache(), always_use_cached_value_for_minutes=1)


    def add_resolver_config(self, cit:str):
        cit = cit_from_str(cit)
        if not cit:
            raise ValueError('the cit could not be parsed. Neither as v1 or v2')
        self._resolver._resolver_configs.add(cit)
        
    def remove_resolver_config(self, resolver_config:str):
        resolver_config = cit_from_str(resolver_config)
        self._resolver._resolver_configs.discard(resolver_config)
        
        
    def process_pac(self, pac_url) -> PacInfo:
        if not isinstance(pac_url, PAC_ID):
            pac = PAC_ID.from_url(pac_url)
        else:
            pac = pac_url
        service_groups = self._resolver.resolve(pac, check_service_status=False, use_issuer_resolver_config=self._use_issuer_resolver_config)
        
        pac_info = PacInfo(pac_id=pac)
                       
        # update service states
        (sg.update_states() for sg in service_groups)
               
        # Services
        sg_user_handovers = []
        for sg in service_groups:
            user_handovers = [s  for s in sg.services if s.service_type == 'userhandover-generic']
            
            if user_handovers:
                sg_user_handovers.append(ServiceGroup(origin=sg.origin, services=user_handovers))
        pac_info.user_handovers = sg_user_handovers
        
        # Actions
        sg_actions = []
        for sg in service_groups:
            actions = [s  for s in sg.services if s.service_type == 'action-generic']
            
            if actions:
                sg_actions.append(ServiceGroup(origin=sg.origin, services=actions))
        pac_info.actions = sg_actions
        
        # Attributes
        attribute_groups = {}
        for sg in service_groups:  
            attributes_urls = [s.url  for s in sg.services if s.service_type == 'attributes-generic']
            for url in attributes_urls:
                ags = {ag.key: pyAttributeGroup.from_attribute_group(ag) for ag in self._attribute_client.get_attributes(url, pac_id=pac.to_url(include_extensions=False), language_preferences=self._language_preferences)}
                if ags:
                    attribute_groups.update(ags)
        pac_info.attribute_groups = attribute_groups
       
        return pac_info
    
    
    
    def update_user_handover_states(self, services, session:requests.Session = None):
        '''Triggers each service to check if the url can be reached'''
        if not _has_internet_connection():
            raise ConnectionError("No Internet Connection")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(s.check_service_status, session=session) for s in services]
            for _ in as_completed(futures):
                pass  # just wait for all to finish
            
            
def _has_internet_connection():
    try:
        requests.head("https://1.1.1.1", timeout=3)
        return True
    except requests.RequestException:
        return False
                
                
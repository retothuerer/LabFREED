from functools import lru_cache
import logging
from typing import Self
from requests import get
from deprecated import deprecated

from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.services import ServiceGroup
from labfreed.pac_id_resolver.cit_v1 import CIT_v1
from labfreed.pac_id_resolver.resolver_config import ResolverConfig



''' Configure pdoc'''
__all__ = ["PAC_ID_Resolver"]

def load_cit(path):
    with open(path, 'r') as f:
        s = f.read()
        return cit_from_str(s)

    
@deprecated("cit version 1 is deprecated. use resolvber config and load with ResolverConfig.from_yaml(s)")
def cit_from_str(s:str, origin:str='') -> CIT_v1|ResolverConfig:
    try:
        cit2 = ResolverConfig.from_yaml(s)
        cit_version = 'v2'
    except Exception as e1:
        cit2 = None
    try:
        cit1 = CIT_v1.from_csv(s, origin)
        cit_version = 'v1'  # noqa: F841
    except Exception as e2:
        cit1 = None
    
    cit = cit2 or cit1 or None
    return cit

@lru_cache
def _get_issuer_resolver_config(issuer:str):
    '''Gets the issuer's cit.'''
    # V2
    url = 'HTTPS://PAC.' + issuer + '/resolver_config.yaml'
    try:
        r = get(url, timeout=2)
        if r.status_code < 400:
            config_str = r.text
            resolver_config = ResolverConfig.from_yaml(config_str)
            return resolver_config
        else: 
            logging.error(f"Could not get CIT V2 form {issuer}")
    except Exception:
        logging.error(f"Could not get CIT V2 form {issuer}")
        
        
    # V1 (as fallback)
    url = 'HTTPS://PAC.' + issuer + '/coupling-information-table'
    try:
        r = get(url, timeout=2)
        if r.status_code < 400:
            config_str = r.text
            cit = CIT_v1.from_csv(config_str, '')
            return cit
        else: 
            logging.error(f"Could not get CIT form {issuer}")
    except Exception:
        logging.error(f"Could not get CIT form {issuer}")
        
    # no cit found
    return None 

    


class PAC_ID_Resolver():
    def __init__(self, resolver_configs:list[ResolverConfig|CIT_v1]=None) -> Self:
        '''Initialize the resolver with coupling information tables'''
        if not resolver_configs:
            resolver_configs = []
        self._resolver_configs = set(resolver_configs)
            
        
    def resolve(self, pac_id:PAC_ID|str, check_service_status=True, use_issuer_resolver_config=True) -> list[ServiceGroup]:
        '''Resolve a PAC-ID'''
        if isinstance(pac_id, str):
            pac_id_catless = PAC_ID.from_url(pac_id, try_pac_cat=False)
            pac_id = PAC_CAT.from_url(pac_id)
        
        # it's likely to
        if isinstance(pac_id, PAC_ID):
            pac_id_catless = PAC_ID.from_url(pac_id.to_url(), try_pac_cat=False)
        else:
            raise ValueError('pac_id is invalid. Should be a PAC-ID in url form or a PAC-ID object')
    
                
        resolver_configs = self._resolver_configs.copy()
        if use_issuer_resolver_config:
            if issuer_resolver_config := _get_issuer_resolver_config(pac_id.issuer):
                resolver_configs.add(issuer_resolver_config)
         
        matches = []
        for cit in resolver_configs:
            if isinstance(cit, CIT_v1):
                # cit v1 has no concept of categories and implied keys. It would treat these segments as value segment
                matches.append(cit.evaluate_pac_id(pac_id_catless))
            else:
                matches.append(cit.evaluate_pac_id(pac_id))
        
        if check_service_status:
            for m in matches:
                m.update_states()   
        return matches
            
    
    
if __name__ == '__main__':
    r = PAC_ID_Resolver()
    r.resolve()

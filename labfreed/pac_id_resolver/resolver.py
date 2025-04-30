import logging
from typing import Self
import yaml
from requests import get



from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.services import ServiceGroup
from labfreed.pac_id_resolver.cit_v1 import CIT_v1
from labfreed.pac_id_resolver.cit_v2 import CIT_v2



''' Configure pdoc'''
__all__ = ["PAC_ID_Resolver"]

def load_cit(path):
    with open(path, 'r') as f:
        s = f.read()
        return cit_from_str(s)

    
def cit_from_str(s:str, origin:str='') -> CIT_v1|CIT_v2:
    try:
        cit_yml= yaml.safe_load(s)
        cit2 = CIT_v2.from_yaml(cit_yml)
        cit_version = 'v2'
    except Exception:
        cit2 = None
    try:
        cit1 = CIT_v1.from_csv(s, origin)
        cit_version = 'v1'
    except Exception:
        cit1 = None
    
    cit = cit2 or cit1 or None
    return cit

def _get_issuer_cit(issuer:str):
    '''Gets the issuer's cit.'''
    url = 'HTTPS://PAC.' + issuer + '/coupling-information-table'
    try:
        r = get(url, timeout=2)
        if r.status_code < 400:
            cit_str = r.text
        else: 
            logging.error(f"Could not get CIT form {issuer}")
            cit_str  = None
    except Exception:
        logging.error(f"Could not get CIT form {issuer}")
        cit_str  = None
    cit = cit_from_str(cit_str, origin=issuer)
    return cit
    


class PAC_ID_Resolver():
    def __init__(self, cits:list[CIT_v2|CIT_v1]=None) -> Self:
        '''Initialize the resolver with coupling information tables'''
        if not cits:
            cits = []
        self._cits = cits
            
        
    def resolve(self, pac_id:PAC_ID|str, check_service_status=True) -> list[ServiceGroup]:
        '''Resolve a PAC-ID'''
        if isinstance(pac_id, str):
            pac_id = PAC_CAT.from_url(pac_id)
                
        if issuer_cit := _get_issuer_cit(pac_id.issuer):
            self._cits.append(issuer_cit)
         
        matches = [cit.evaluate_pac_id(pac_id) for cit in self._cits]
        
        if check_service_status:
            for m in matches:
                m.update_states()   
        return matches
            
    
    
if __name__ == '__main__':
    r = PAC_ID_Resolver()
    r.resolve()

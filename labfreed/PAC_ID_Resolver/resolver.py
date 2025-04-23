import os
from typing import Self
import yaml



from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.services import ServiceGroup
from labfreed.pac_id_resolver.cit_v1 import CIT_v1
from labfreed.pac_id_resolver.cit_v2 import CIT_v2



''' Configure pdoc'''
__all__ = ["PAC_ID_Resolver"]

def load_cit(path):
    with open(path, 'r') as f:
        cit_yml= yaml.safe_load(f)
        cit = CIT_v2.from_yaml(cit_yml)
        return cit


class PAC_ID_Resolver():
    def __init__(self, cits:list[CIT_v2|CIT_v1]=None) -> Self:
        '''Initialize the resolver with coupling information tables'''
        if not cits:
            cits = []
        self._cits = cits
        
        # load the default cit
        dir = os.path.dirname(__file__)
        fn ='cit.yaml'
        p = os.path.join(dir, fn)       
        with open(p, 'r') as f:
            cit = yaml.safe_load(f)
            cit = CIT_v2.from_yaml(cit)
            self._cits.append(cit)
        
        
    def resolve(self, pac_id:PAC_ID|str) -> list[ServiceGroup]:
        '''Resolve a PAC-ID'''
        if isinstance(pac_id, str):
            pac_id = PAC_CAT.from_url(pac_id)
        
        pac_id_json = pac_id.model_dump(by_alias=True)
        
        
        # dir = os.path.dirname(__file__)
        # p = os.path.join(dir, 'pac-id.json')
        # with open(p , 'r') as f:
        #     _json = f.read()
        #     pac_id_json = json.loads(_json)
        
        matches = [cit.evaluate_pac_id(pac_id_json) for cit in self._cits]
        return matches
            


    
    
if __name__ == '__main__':
    r = PAC_ID_Resolver()
    r.resolve()

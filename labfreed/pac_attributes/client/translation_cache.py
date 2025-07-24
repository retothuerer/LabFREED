

    
from typing import Protocol

from labfreed.utilities.translations import Term


class TranslationCache(Protocol):
    def get(self, ontology:str, key:str) -> Term:
        pass
        
    def update(self, ontology:str, translations:list[Term]):
        pass
    

            
    
class TranslationMemoryCache(TranslationCache):
    def __init__(self):
        self._store = dict()
    
    def get(self, ontology:str, key:str) -> Term:
        k = self._generate_dict_key(ontology=ontology, key=key)
        
        if e:= self._store.get(k):
            t = Term.model_validate(e)
            return t
        else:
            return None
        
    def update(self, ontology:str, translations:Term|list[Term]):
        if not isinstance(translations, list):
            translations = [translations]
            
        for t in translations:
            k = self._generate_dict_key(ontology=ontology, key=t.key)
            self._store.update({k: t.model_dump()})
    
    @staticmethod
    def _generate_dict_key(ontology:str, key:str):
        key = ontology +";"+ key
        return key
   
    
    
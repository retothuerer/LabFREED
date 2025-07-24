from abc import ABC, abstractmethod, abstractproperty
import json

from pydantic import ValidationError
from translations import TranslationsForOntology, Term

class OnthologyTranslationDataSource(ABC):
    @abstractproperty
    def onthology(self):
        pass
    @abstractmethod
    def get_translations_for(self, key:str) -> Term:
        pass
    

class DictTranslationDataSource(OnthologyTranslationDataSource):
    def __init__(self, onthology:str, data:TranslationsForOntology) -> None:
        self._onthology = onthology
        self._data = data
        
    def get_translations_for(self, key:str) -> Term:
        t = self._data.translations_for_term(key)
        return t
    
    @property
    def onthology(self):
        return self._onthology
   

    
class JsonFileTranslationDataSource(DictTranslationDataSource):
    def __init__(self, path:str) -> None:
        with open(path) as f:
            data = json.load(f)
        try:
            super().__init__(data=data)
        except ValidationError as e:
            e.add_note('Json must be convertible to OnthologyTranslationDataSource')
            raise e
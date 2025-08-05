from abc import ABC, abstractmethod, abstractproperty
import json

from pydantic import ValidationError
import rich
from labfreed.utilities.translations import Terms, Term

class TranslationDataSource(ABC):

    @abstractmethod
    def get_translations_for(self, key:str) -> Term:
        pass
    
    @abstractproperty
    def supported_languages(self) -> set[str]:
        pass
    

class DictTranslationDataSource(TranslationDataSource):
    def __init__(self, data:Terms, supported_languages:set[str]) -> None:
        
        self._data = data
        
        #check that there are translations for the supported languages. Adjust supported_languages if needed
        supported_languages = set(supported_languages) # to ensure uniqueness
        for language in supported_languages.copy():
            if translation_missing := self._list_missing_translations_to(language):
                rich.print(f"[bold yellow]WARNING:[/bold yellow]: Translation to '{language}' missing for {translation_missing}")
                supported_languages.remove(language)
                
        self._supported_languages = supported_languages
        
    def _list_missing_translations_to(self, language:str):
        translation_missing_for_keys = []
        for term in self._data.terms:
            if language not in [t.language_code for t in term.translations]:
                translation_missing_for_keys.append(term.key)
        return translation_missing_for_keys 
    
    def get_translations_for(self, key:str) -> Term:
        t = self._data.translations_for_term(key)
        return t
    
    @property
    def supported_languages(self) -> set[str]:
        return self._supported_languages
    
    
   

    
class JsonFileTranslationDataSource(DictTranslationDataSource):
    def __init__(self, path:str) -> None:
        with open(path) as f:
            data = json.load(f)
        try:
            super().__init__(data=data)
        except ValidationError as e:
            e.add_note('Json must be convertible to OnthologyTranslationDataSource')
            raise e
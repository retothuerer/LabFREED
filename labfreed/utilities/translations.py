from pydantic import BaseModel, model_validator
from typing import Any, List, Optional
import re


class Translation(BaseModel):
    language_code: str
    text: str
    
    @staticmethod
    def create(language_code:str, text:str):
        '''provides a shorter form to init the model without the need to use keywords only'''
        return Translation(language_code=language_code, text=text)
    

    @model_validator(mode="after")
    def validate_language(self):
        if not re.fullmatch(r"^[a-z]{2,3}(-[a-z]{2,3})?$", self.language_code.lower()):
            raise ValueError(f"Invalid language code: {self.language_code}")
        return self
    
    
    @property
    def language(self) -> str:
        return self.language_code.split("-")[0].lower()

    @property
    def region(self) -> Optional[str]:
        parts = self.language_code.split("-")
        return parts[1].upper() if len(parts) == 2 else None
    
class Term(BaseModel):
    key: str
    translations: List[Translation]
    
    @staticmethod
    def create(key:str, translations:List[Translation]|List[tuple]):
        '''provides a shorter form to init the model without the need to use keywords only'''
        translations = [ t if isinstance(t, Translation) else Translation.create(*t) for t in translations]
        return Term(key=key, translations=translations)
    
    
    def in_language(self, language_key: str) -> str | None:
        for t in self.translations:
            if t.language_code == language_key:
                return t.text
        return None
    
class TranslationsForOntology(BaseModel):
    ontology: str
    terms: List[Term]

    def translations_for_term(self, term_key: str) -> Term | None:
        for t in self.terms:
            if t.key == term_key:
                return t
        return None
    


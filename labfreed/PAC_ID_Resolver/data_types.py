from pydantic import BaseModel, Field, field_validator
from rich import print
from rich.table import Table

from labfreed.validation import BaseModelWithValidationMessages


class CITEntry(BaseModelWithValidationMessages):
    service_name: str
    application_intents:list[str]
    service_type:str
    template_url:str
    

class CITBlock(BaseModelWithValidationMessages):
    applicable_if: str  = Field(default='True', alias='if')
    entries: list[CITEntry]
    
    @field_validator('applicable_if', mode='before')
    @classmethod
    def convert_if(cls, v):
        return v if v is not None else 'True'
    

class CIT(BaseModelWithValidationMessages):
    origin: str = ''
    macros:dict = Field(default_factory=dict)
    cit: list[CITBlock] = Field(default_factory=list)
    
    

    
class Service(BaseModelWithValidationMessages):
    service_name: str
    application_intents:list[str]
    service_type:str
    url:str
    
    
class CITEvaluated(BaseModelWithValidationMessages):
    origin: str = ""
    services: list[Service] = Field(default_factory=list)
    
    def __str__(self):
        out = [f'CIT (origin {self.origin})']
        for s in self.services:
            out.append(f'{s.service_name}\t\t\t{s.url}')
        return '\n'.join(out)
    
    def print(self):
        table = Table(title=f"Services from origin '{self.origin}")

        table.add_column("Service Name")
        table.add_column("URL")
        
        for s in self.services:
            table.add_row(s.service_name, s.url)

        print(table)
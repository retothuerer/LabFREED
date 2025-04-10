from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum, auto
from pydantic import BaseModel, Field, field_validator
from requests import RequestException, request, ConnectionError, ReadTimeout
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
    
    

class ServiceState(Enum):
    ACTIVE = auto()
    INACTIVE = auto()
    UNKNOWN = auto()
    
class Service(BaseModelWithValidationMessages):
    service_name: str
    application_intents:list[str]
    service_type:str
    url:str
    active:ServiceState =ServiceState.UNKNOWN
    
    def check_state(self):
        try:
            r = request('get',self.url, timeout=2)
            if r.status_code < 400:
                self.active = ServiceState.ACTIVE
            else: 
                self.active = ServiceState.INACTIVE
        except RequestException as e:
            print(f"Request failed: {e}")
            self.active = ServiceState.INACTIVE
            
    
class CITEvaluated(BaseModelWithValidationMessages):
    origin: str = ""
    services: list[Service] = Field(default_factory=list)
    
    def update_states(self):
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(s.check_state) for s in self.services]
            for _ in as_completed(futures):
                pass  # just wait for all to finish
    
    def __str__(self):
        out = [f'CIT (origin {self.origin})']
        for s in self.services:
            out.append(f'{s.service_name}\t\t\t{s.url}')
        return '\n'.join(out)
    
    def print(self):
        table = Table(title=f"Services from origin '{self.origin}")

        table.add_column("Service Name")
        table.add_column("URL")
        table.add_column('Reachable')
        
        for s in self.services:
            table.add_row(s.service_name, s.url, s.active.name)

        print(table)
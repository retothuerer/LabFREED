
from enum import auto, Enum

from pydantic import Field
from requests import RequestException, get, head

from concurrent.futures import ThreadPoolExecutor, as_completed

from rich import print
from rich.table import Table

from labfreed.labfreed_infrastructure import LabFREED_BaseModel


class ServiceStatus(Enum):
    ACTIVE = auto()
    INACTIVE = auto()
    UNKNOWN = auto()
    
class Service(LabFREED_BaseModel):
    service_name: str
    application_intents:list[str]
    service_type:str
    url:str
    status:ServiceStatus =ServiceStatus.UNKNOWN
    
    def check_service_status(self):
        '''Checks the availability of the service.'''
        try:
            r = head(self.url, timeout=2)
            if r.status_code < 400:
                self.status = ServiceStatus.ACTIVE
            else: 
                self.status = ServiceStatus.INACTIVE
        except RequestException as e:
            print(f"Request failed: {e}")
            self.status = ServiceStatus.INACTIVE
             
    
class ServiceGroup(LabFREED_BaseModel):
    """ Services with common origin. The result of resolving a PAC-ID against a CIT"""
    origin: str = ""
    services: list[Service] = Field(default_factory=list)
    
    def update_states(self):
        '''Triggers each service to check if the url can be reached'''
        if not _has_internet_connection():
            raise ConnectionError("No Internet Connection")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(s.check_service_status) for s in self.services]
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
            table.add_row(s.service_name, s.url, s.status.name)

        print(table)
        
        
def _has_internet_connection():
    try:
        get("https://1.1.1.1", timeout=3)
        return True
    except RequestException:
        return False
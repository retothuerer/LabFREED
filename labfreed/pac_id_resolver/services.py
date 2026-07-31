
from enum import StrEnum

from pydantic import Field

from rich import print
from rich.table import Table

from labfreed.labfreed_infrastructure import LabFREED_BaseModel


class ServiceStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"

class Service(LabFREED_BaseModel):
    service_name: str
    application_intents:list[str]
    service_type:str
    url:str
    status:ServiceStatus =ServiceStatus.UNKNOWN


class ServiceGroup(LabFREED_BaseModel):
    """ Services with common origin. The result of resolving a PAC-ID against a CIT"""
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
        table.add_column("Service Type")
        table.add_column('Reachable')

        for s in self.services:
            table.add_row(s.service_name, s.url, s.service_type, s.status.name)

        print(table)



from pydantic import BaseModel, Field
from labfreed.pac_attributes.python_convenience.py_attributes import pyAttributes
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.services import ServiceGroup


class PacInfo(BaseModel):
    pac_id:PAC_ID
    display_name:str|None = None
    user_handovers: list[ServiceGroup] = Field(default_factory=list)
    attributes:pyAttributes = Field(default_factory=list)
    
    @property
    def pac_url(self):
        return self.pac_id.to_url(include_extensions=False)
    
    @property
    def main_category(self):
        if isinstance(self.pac_id, PAC_CAT):
            return self.pac_id.categories[0]
        else:
            return None
        
    @property
    def attached_data(self):
        return self.pac_id.get_extension_of_type('TREX')
    
    @property
    def summary(self):
        return self.pac_id.get_extension('SUM')
        
        
        
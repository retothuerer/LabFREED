import logging
from PAC_ID.data_model import Extension
from base36 import from_base36, to_base36
from pydantic import BaseModel

class DisplayNames(Extension, BaseModel):
    display_names: list[str]
       
    @property
    def name(self)->str:
        return 'N'
    
    @property
    def type(self)->str:
        return 'N'
    
    @property
    def data(self)->str:
        return '/'.join([to_base36(dn) for dn in self.display_names])
    
    @staticmethod
    def from_spec_fields(name, type, data):
        if name != 'N':
            logging.warning(f'Name {name} was given, but this extension should only be used with name "N". Will ignore input')
            
        if type != 'N':
            logging.warning(f'Type {name} was given, but this extension should only be used with type "N". Will try to parse data as display names')
        
        display_names = [from_base36(b36) for b36 in data.split('/')]
         
        return DisplayNames(display_names=display_names)



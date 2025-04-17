import logging
from pydantic import BaseModel
from labfreed.pac_id.extension import Extension
from labfreed.utilities.base36 import from_base36, to_base36


class DisplayName(Extension, BaseModel):
    display_name: str       
    @property
    def name(self)->str:
        return 'N'
    
    @property
    def type(self)->str:
        return 'N'
    
    @property
    def data(self)->str:
        # return '/'.join([to_base36(dn) for dn in self.display_name])
        return to_base36(self.display_name) 
    
    @staticmethod
    def create(*, name, type, data):
        if name != 'N':
            logging.warning(f'Name {name} was given, but this extension should only be used with name "N". Will ignore input')
            
        if type != 'N':
            logging.warning(f'Type {name} was given, but this extension should only be used with type "N". Will try to parse data as display names')
        
        display_name = from_base36(data)
         
        return DisplayName(display_name=display_name)
    
    def __str__(self):
        return 'Display name: '+ self.display_name


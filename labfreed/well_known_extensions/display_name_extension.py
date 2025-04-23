import logging
from typing import Literal, Self
from pydantic import computed_field
from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_id.extension import ExtensionBase
from labfreed.utilities.base36 import from_base36, to_base36


class DisplayNameExtension(ExtensionBase, LabFREED_BaseModel):
    name:Literal['N'] = 'N'
    type:Literal['N'] = 'N'
    display_name: str       
    
    @computed_field
    @property
    def data(self)->str:
        # return '/'.join([to_base36(dn) for dn in self.display_name])
        return to_base36(self.display_name) 
    
    @staticmethod
    def from_extension(ext:ExtensionBase) -> Self:
        return DisplayNameExtension.create(name=ext.name,
                                  type=ext.type,
                                  data=ext.data)
    
    @staticmethod
    def create(*, name, type, data):
        if name != 'N':
            logging.warning(f'Name {name} was given, but this extension should only be used with name "N". Will ignore input')
            
        if type != 'N':
            logging.warning(f'Type {name} was given, but this extension should only be used with type "N". Will try to parse data as display names')
        
        display_name = from_base36(data)
         
        return DisplayNameExtension(display_name=display_name)
    
    def __str__(self):
        return 'Display name: '+ self.display_name


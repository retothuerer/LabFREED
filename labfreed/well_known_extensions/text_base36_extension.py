import logging
from typing import Literal, Self
from pydantic import computed_field
from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_id.extension import ExtensionBase
from labfreed.utilities.base36 import from_base36, to_base36


class TextBase36Extension(ExtensionBase, LabFREED_BaseModel):
    name:str 
    type:Literal['TEXT'] = 'TEXT'
    text: str       
    
    @computed_field
    @property
    def data(self)->str:
        # return '/'.join([to_base36(dn) for dn in self.display_name])
        return to_base36(self.text).root
    
    @staticmethod
    def from_extension(ext:ExtensionBase) -> Self:
        return TextBase36Extension.create(name=ext.name,
                                  type=ext.type,
                                  data=ext.data)
    
    @staticmethod
    def create(*, name, type, data):
            
        if type != 'TEXT':
            logging.warning(f'Type {name} was given, but this extension should only be used with type "TEXT". Will try to parse data as display names')
        
        text = from_base36(data)
         
        return TextBase36Extension(name=name, text=text)
    
    def __str__(self):
        return 'Text: '+ self.text


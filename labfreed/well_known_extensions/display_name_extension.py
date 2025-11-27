import logging
from typing import Literal, Self
from pydantic import  model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_id.extension import ExtensionBase
from labfreed.well_known_extensions.text_base36_extension import TextBase36Extension

from labfreed.utilities.base36 import from_base36


class DisplayNameExtension(TextBase36Extension, LabFREED_BaseModel):
    name:Literal['N'] = 'N'
    type:Literal['TEXT'] = 'TEXT'
    
    @model_validator(mode='before')
    def move_display_name_to_text(cls, data):
        # if display_name provided, move it to text
        if isinstance(data, dict) and 'display_name' in data:
            data['text'] = data.pop('display_name')
        return data
    
    @staticmethod
    def from_extension(ext:ExtensionBase) -> Self:
        return DisplayNameExtension.create(name=ext.name,
                                  type=ext.type,
                                  data=ext.data)

    @property
    def display_name(self) -> str:
        return self.text 
    
    
    @staticmethod
    def create(*, name, type, data):
        if name != 'N':
            logging.warning(f'Name {name} was given, but this extension should only be used with name "N". Will ignore input')
            
        if type != 'TEXT':
            logging.warning(f'Type {name} was given, but this extension should only be used with type "TEXT". Will try to parse data as display names')
        
        display_name = from_base36(data)
         
        return DisplayNameExtension(display_name=display_name)
    
    def __str__(self):
        return 'Display name: '+ self.display_name


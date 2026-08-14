import logging
from typing import Literal, Self
from pydantic import computed_field
from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_id.extension import ExtensionBase
from labfreed.pac_id.keyed_values import KeyedValue, ExtensionOrigin
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
            logging.warning(f'Type {type} was given, but this extension should only be used with type "TEXT". Will try to parse data as display names')
        
        text = from_base36(data)
         
        return TextBase36Extension(name=name, text=text)
    
    def values_for_key(self, key: str) -> list[KeyedValue]:
        '''Overrides the ExtensionBase default to return the decoded .text rather than
        the still-base36-encoded .data - this is what lets DisplayNameExtension (a
        subclass, name fixed to 'N') answer values_for_key('N') correctly without its
        own override.'''
        if self.name == key:
            return [KeyedValue(value=[self.text], origin=ExtensionOrigin(extension_name=self.name))]
        return []

    def __str__(self):
        return 'Text: '+ self.text


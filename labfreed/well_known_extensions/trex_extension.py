from typing import Literal, Self

from pydantic import Field, computed_field 
from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_id.extension import ExtensionBase
from labfreed.trex.trex import TREX


class TREX_Extension(ExtensionBase, LabFREED_BaseModel):
    name:str
    type:Literal['TREX'] = 'TREX'
    trex:TREX
           
    @computed_field
    @property
    def data(self)->str:
        trex_str = self.trex.serialize()
        return trex_str
        
    @staticmethod
    def from_extension(ext:ExtensionBase) -> Self:
        return TREX_Extension.create(name=ext.name,
                                    type=ext.type,
                                    data=ext.data)
    
    @staticmethod
    def create(*, name, data, type='TREX'):
        trex_extension = TREX_Extension(name= name, trex = TREX.deserialize(data))
        return trex_extension
    
   
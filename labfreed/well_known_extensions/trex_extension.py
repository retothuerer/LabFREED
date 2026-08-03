from typing import Literal, Self

from pydantic import computed_field 
from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_id.extension import ExtensionBase
from labfreed.trex.trex import Spec_T_REX


class TREX_Extension(ExtensionBase, LabFREED_BaseModel):
    name:str
    type:Literal['TREX'] = 'TREX'
    trex:Spec_T_REX

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
        trex_extension = TREX_Extension(name= name, trex = Spec_T_REX.deserialize(data))
        return trex_extension
    
   
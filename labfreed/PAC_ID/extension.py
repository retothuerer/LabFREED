
from abc import ABC, abstractproperty

from pydantic import PrivateAttr,computed_field, model_validator

from labfreed.labfreed_infrastructure import LabFREED_BaseModel

    
class ExtensionBase(ABC):
    name: str
    type: str


    @abstractproperty
    def data(self) -> str:
        raise NotImplementedError("Subclasses must implement 'data'")
    
    


class Extension(LabFREED_BaseModel,ExtensionBase):
    '''Implementation of Extension for unknown extension types'''
    name:str
    type:str
    data_:str
    
    @property
    def data(self) -> str:
        return self.data_
       
    @staticmethod
    def create(*, name, type, data):
        return Extension(name=name, type=type, data=data)
    
    @model_validator(mode='before')
    @classmethod
    def move_data_field(cls, values):
        if "data" in values:
            values["data_"] = values.pop("data")
        return values
    
    model_config = {
        "extra": "allow",  # Allow extra keys during pre-validation
    }
    
    def __str__(self):
        return f'{self.name}${self.type}/{self.data}'
    
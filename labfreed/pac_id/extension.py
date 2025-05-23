
from abc import ABC, abstractproperty

from pydantic import model_validator

from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel

    
class ExtensionBase(ABC):
    name: str|None
    type: str|None


    @abstractproperty
    def data(self) -> str:
        raise NotImplementedError("Subclasses must implement 'data'")
    
    def __str__(self):
        if self.name and self.type:
            return f'{self.name}${self.type}/{self.data}'
        else:
            return self.data
    


class Extension(LabFREED_BaseModel,ExtensionBase):
    '''Implementation of Extension for unknown extension types'''
    name:str|None
    type:str|None
    data_:str
    
    @property
    def data(self) -> str:
        return self.data_
       
    @staticmethod
    def create(*, name:str|None, type:str|None, data:str):
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
        
    @model_validator(mode='after')
    def validate_model(self):
        if self.name and not self.type:
            raise ValueError('Extension has a name, but no type. Either set both or none')
        
        if self.type and not self.name:
            raise ValueError('Extension has a type, but no name. Either set both or none')
        
        if not self.type and not self.name:
            self._add_validation_message(msg="Extensions has no name and type. It is RECOMMENDED to specify name and type.",
                                         level=ValidationMsgLevel.RECOMMENDATION, 
                                         source=f"Extension '{self.data[0:10] if len(self.data)>10 else self.data}'",
                                         highlight_pattern=self.data)
        
        return self
            
        
    
    model_config = {
        "extra": "allow",  # Allow extra keys during pre-validation
    }
    


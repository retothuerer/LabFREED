
from abc import ABC, abstractmethod

from pydantic import computed_field, model_validator

from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel

    
class ExtensionBase(ABC):
    name: str|None
    type: str|None


    @property
    @abstractmethod
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
    
    @computed_field
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
        source = f"Extension '{self.data[0:10] if len(self.data) > 10 else self.data}'"

        if self.name and not self.type:
            self._add_validation_message(msg="Extension has a name, but no type. Either set both or none.",
                                         level=ValidationMsgLevel.ERROR,
                                         source=source,
                                         highlight_pattern=self.name)

        if self.type and not self.name:
            self._add_validation_message(msg="Extension has a type, but no name. Either set both or none.",
                                         level=ValidationMsgLevel.ERROR,
                                         source=source,
                                         highlight_pattern=self.type)

        if not self.type and not self.name:
            self._add_validation_message(msg="Extensions has no name and type. It is RECOMMENDED to specify name and type.",
                                         level=ValidationMsgLevel.RECOMMENDATION,
                                         source=source,
                                         highlight_pattern=self.data)

        if '/' in self.data:
            self._add_validation_message(msg="Extension data must not contain the character '/'.",
                                         level=ValidationMsgLevel.ERROR,
                                         source=source,
                                         highlight_pattern=self.data,
                                         highlight_sub=['/'])

        if self.type:
            from labfreed.well_known_extensions import default_extension_interpreters
            if self.type not in default_extension_interpreters:
                self._add_validation_message(msg=f"'{self.type}' is not a well-known extension type. It is RECOMMENDED to use a well-known extension type.",
                                             level=ValidationMsgLevel.RECOMMENDATION,
                                             source=source,
                                             highlight_pattern=self.type)

        return self
            
        
    
    model_config = {
        "extra": "allow",  # Allow extra keys during pre-validation
    }
    


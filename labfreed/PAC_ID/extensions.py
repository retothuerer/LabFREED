
from abc import ABC, abstractproperty, abstractstaticmethod

from labfreed.validation import LabFREED_BaseModel
from labfreed.PAC_ID.data_model import PACID


    

class Extension(ABC, LabFREED_BaseModel): 
    
    @abstractproperty
    def name(self)->str:
        pass
    
    @abstractproperty
    def type(self)->str:
        pass
    
    @abstractproperty
    def data(self)->str:
        pass
    
    @abstractstaticmethod
    def from_spec_fields(*, name, type, data):
        pass
    
    def __str__(self):
        return f'{self.name}${self.type}/{self.data}'
    
    

class UnknownExtension(Extension):
    name_:str
    type_:str
    data_:str
    
    @property
    def name(self)->str:
        return self.name_
    
    @property
    def type(self)->str:
        return self.type_
    
    @property
    def data(self)->str:
        return self.data_
       
    @staticmethod
    def from_spec_fields(*, name, type, data):
        return UnknownExtension(name_=name, type_=type, data_=data)
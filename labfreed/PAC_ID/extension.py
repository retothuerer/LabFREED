
from abc import ABC, abstractproperty, abstractstaticmethod
from typing import Self

from labfreed.labfreed_infrastructure import LabFREED_BaseModel



class Extension(ABC, LabFREED_BaseModel): 
    ''' Represents a PAC-ID extension.'''
    
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
    def create(*, name, type, data) -> Self:
        '''Creates the Extension from the name, type and data strings 
        example: *EXTNAME$MYEXTTYPE/FOOOOBAR
        > create('EXTNAME', 'MYEXTTYPE','FOOBAR')
        '''
        pass
    
    
    def __str__(self):
        return f'{self.name}${self.type}/{self.data}'
    
    
    
    

class UnknownExtension(Extension):
    '''Implementation of Extension for unknown extension types'''
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
    def create(*, name, type, data):
        return UnknownExtension(name_=name, type_=type, data_=data)
from abc import ABC
import re
from typing import Literal
from pydantic import Field, model_validator
from labfreed.well_known_keys.unece.unece_units import unece_unit_codes
from labfreed.labfreed_infrastructure import ValidationMsgLevel
from labfreed.trex.trex_base_models import AlphanumericValue, BinaryValue, BoolValue, DateValue, ErrorValue, NumericValue, TREX_Segment, TextValue, Value



class ValueSegment(TREX_Segment, Value, ABC):
    '''@private: Abstract base class for value segments'''
    type:str
    
    @model_validator(mode='after')
    def _validate_type(self):
        valid_types = valid_types = unece_unit_codes() + ['T.D', 'T.B', 'T.A', 'T.T', 'T.X', 'E']
        if self.type not in valid_types:
            self._add_validation_message(
                    source=f"TREX value segment {self.key}",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Type {self.type} is invalid. Must be 'T.D', 'T.B', 'T.A', 'T.T', 'T.X', 'E' or a UNECE unit",
                    highlight_pattern = self.type
            )
        return self
        
    
    def serialize(self) -> str:
        return f'{self.key}${self.type}:{self.value}'
    
    
class NumericSegment(ValueSegment, NumericValue):
    '''Represents a TREX segment holding a numeric value'''
    type: str 
    key:str   
    value:str
    
class DateSegment(ValueSegment, DateValue):
    '''Represents a TREX segment holding a date'''
    type: Literal['T.D'] = Field('T.D', frozen=True)
    key:str   
    value:str
          
class BoolSegment(ValueSegment, BoolValue):
    '''Represents a TREX segment holding a boolean value'''
    type: Literal['T.B']  = Field('T.B', frozen=True) 
    key:str   
    value:str
class AlphanumericSegment(ValueSegment, AlphanumericValue):
    '''Represents a TREX segment holding a alphanumeric text'''
    type: Literal['T.A'] = Field('T.A', frozen=True)
    key:str   
    value:str
class TextSegment(ValueSegment, TextValue):
    '''Represents a TREX segment holding a text with arbitrary characters'''
    type: Literal['T.T'] = Field('T.T', frozen=True)
    key:str   
    value:str
    
class BinarySegment(ValueSegment, BinaryValue):
    '''Represents a TREX segment holding binary data'''
    type: Literal['T.X'] = Field('T.X', frozen=True)
    key:str   
    value:str
    
class ErrorSegment(ValueSegment, ErrorValue):
    '''Represents a TREX segment which has erroneous content'''
    type: Literal['E'] = Field('E', frozen=True)
    key:str   
    value:str
                     

def _deserialize_value_segment_from_trex_segment_str(trex_segment_str) -> ValueSegment:
    #re_scalar_pattern = re.compile(f"(?P<name>[\w\.-]*?)\$(?P<unit>[\w\.]*?):(?P<value>.*)")
    re_scalar_pattern = re.compile("(?P<name>.+?)\$(?P<unit>.+?):(?P<value>.+)")
    matches = re_scalar_pattern.match(trex_segment_str)
    if not matches:
        return None
    
    key, type_, value = matches.groups()
    
    match type_:
        case 'T.D':
            out = DateSegment(key=key, value=value, type=type_)
        case 'T.B':
            out = BoolSegment(key=key, value=value, type=type_)
        case 'T.A':
            out = AlphanumericSegment(key=key, value=value, type=type_)
        case 'T.T':
            out = TextSegment(key=key, value=value, type=type_)  
        case 'T.X':
            out = BinarySegment(key=key, value=value, type=type_) 
        case 'E':
            out = ErrorSegment(key=key, value=value, type=type_)
        case _:
            out = NumericSegment(value=value, key=key, type=type_)
                    
    return out    
    

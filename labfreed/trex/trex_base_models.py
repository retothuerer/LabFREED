from datetime import date, datetime, time
import logging
import re



from pydantic import PrivateAttr,  field_validator, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel, _quote_texts
from abc import ABC, abstractclassmethod,  abstractmethod

from labfreed.utilities.base36 import base36, to_base36, from_base36


''' Configure pdoc'''
v_segs  = ["NumericSegment", 
           "DateSegment", 
           "BoolSegment", 
           "AlphanumericSegment", 
           "TextSegment", 
           "BinarySegment"]
__all__ = ["TREX"] + v_segs + ["TableSegment"]  # noqa: F822

            
           

class Value(LabFREED_BaseModel, ABC):
    '''@private
    Helper to add validation for various types to ValueSegments and Tables
    '''
    value:str 
    
    def serialize(self):
        return self.value
        
    @abstractclassmethod
    def _from_python_type(cls, v):
        ...
        
    @abstractmethod
    def _value_to_python_type(self):
        ...
        
        
class NumericValue(Value):
    @field_validator('value', mode='before')
    @classmethod
    def _from_python_type(cls, v:str| int|float):
        if isinstance(v, str):
            return v
        return str(v)
        
    @model_validator(mode='after')
    def _validate(self):
        value = self.value
        if not_allowed_chars := set(re.sub(r'[0-9\.\-E]', '', value)):
            self._add_validation_message(
                source=f"TREX numeric value {value}",
                level=ValidationMsgLevel.ERROR,
                msg=f"Characters {_quote_texts(not_allowed_chars)} are not allowed in quantity segment. Base36 encoding only allows A-Z0-9",
                highlight_pattern = f'{value}',
                highlight_sub=not_allowed_chars
            )
        if not re.fullmatch(r'-?\d+(\.\d+)?(E-?\d+)?', value):
            self._add_validation_message(
                source=f"TREX numeric value {value}",
                level=ValidationMsgLevel.ERROR,
                msg=f"{value} cannot be converted to number",
                highlight_pattern = f'{value}'               
            )
        return self
    
    def _value_to_python_type(self) -> str:
        v = float(self.value)  
        if '.' not in self.value and 'E' not in self.value: 
            return int(v)
        else:
            return v


class DateValue(Value):
    _date_time_dict:dict|None = PrivateAttr(default=None)
    @field_validator('value', mode='before')
    @classmethod
    def _from_python_type(cls, v:str| date|time|datetime):
        if isinstance(v, str):
            return v
        
        sd = ""
        st = ""
        if isinstance(v, date) or isinstance(v, datetime):
            sd = v.strftime('%Y%m%d')
        if isinstance(v, time) or isinstance(v, datetime):
            if v.microsecond:
                st = v.strftime("T%H%M%S.") + f"{v.microsecond // 1000:03d}"
            elif v.second:
                st = v.strftime("T%H%M%S")
            else:
                st = v.strftime("T%H%M")
                         
        return sd + st
    
    @model_validator(mode='after')
    def _validate(self):
        pattern:str = r'((?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}))?(T(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})?(\.(?P<millisecond>\d{3}))?)?'
        value=self.value
        if not re.fullmatch(pattern, value):
            self._add_validation_message(
                source=f"TREX date value {value}",
                level=ValidationMsgLevel.ERROR,
                msg=f'{value} is not in a valid format. Valid format for date: YYYYMMDD; Valid for time: THHMM, THHMMSS, THHMMSS.SSS; Datetime any combination of valid date and time',
                highlight_pattern = f'{value}'
            )
            return self
            
        matches = re.match(pattern, value)       
        d = matches.groupdict()  
        d = {k: int(v) for k,v in d.items() if v }
        if 'millisecond' in d.keys():
            ms = d.pop('millisecond')
            d.update({'microsecond': ms * 1000})
        try:
            if d.get('year'): # input is only a time
                datetime(**d)
            else:
                time(**d)
        except ValueError:
            self._add_validation_message(
                source=f"TREX date value {value}",
                level=ValidationMsgLevel.ERROR,
                msg=f'{value} is no valid date or time.',
                highlight_pattern = f'{value}'
            )
            
        self._date_time_dict = d
        return self
    
    def _value_to_python_type(self) -> str:
        d = self._date_time_dict
        if d.get('year') and d.get('hour'): # input is only a time
            return datetime(**d)
        elif d.get('year'):
            return date(**d)
        else:
            return time(**d)
    
   
class BoolValue(Value):
    @field_validator('value', mode='before')
    @classmethod
    def _from_python_type(cls, v:str| bool):
        if isinstance(v, str):
            return v
        
        return 'T' if v else 'F'

    @model_validator(mode='after')
    def _validate(self):
        if self.value not in ['T', 'F']:
            self._add_validation_message(
                source=f"TREX boolean value {self.value}",
                level= ValidationMsgLevel.ERROR,
                msg=f'{self.value} is no valid boolean. Must be T or F',
                highlight_pattern = f'{self.value}',
                highlight_sub=[c for c in self.value]
            )
        return self
    
    def _value_to_python_type(self) -> str:
        if self.value == 'T':
            return True
        elif self.value == 'F':
            return False
        else:
            Exception(f'{self} is not valid boolean. That really should not have been possible -- Contact the maintainers of the library')
                    
                    
class AlphanumericValue(Value):
    @field_validator('value', mode='before')
    @classmethod
    def _from_python_type(cls, v:str):
        return v
        
    @model_validator(mode='after')
    def _validate(self):
        if re.match(r'[a-z]', self.value):
            self._add_validation_message(
                    source=f"TREX value {self.value}",
                    level= ValidationMsgLevel.ERROR,
                    msg="Lower case characters are not allowed.",
                    highlight_pattern = self.value
            )
            
        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.value)):
            self._add_validation_message(
                    source=f"TREX value {self.value}",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Characters {_quote_texts(not_allowed_chars)} are not allowed in alphanumeric segment",
                    highlight_pattern = self.value,
                    highlight_sub=not_allowed_chars
            )
        return self
           
    def _value_to_python_type(self) -> str:
        return self.value
    
    
class TextValue(Value):
    @field_validator('value', mode='before')
    @classmethod
    def _from_python_type(cls, v:base36|str):
        if isinstance(v, str):
            logging.info('Got str for text value > converting to base36')
            return to_base36(v).root
        else:
            return v.root
        
    @model_validator(mode='after')
    def _validate(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9]', '', self.value)):
            self._add_validation_message(
                    source=f"TREX value {self.value}",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Characters {_quote_texts(not_allowed_chars)} are not allowed in text segment. Base36 encoding only allows A-Z0-9",
                    highlight_pattern = self.value,
                    highlight_sub=not_allowed_chars
            )
        return self
              
    def _value_to_python_type(self) -> str:
        decoded = from_base36(self.value)
        return decoded
    
    
class BinaryValue(Value):
    @field_validator('value', mode='before')
    @classmethod
    def _from_python_type(cls, v:base36|str):
        if isinstance(v, str):
            return v
        else:
            return v.root
        
    @model_validator(mode='after')
    def _validate(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9]', '', self.value)):
           self._add_validation_message(
                    source=f"TREX value {self.value}",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Characters {_quote_texts(not_allowed_chars)} are not allowed in text segment. Base36 encoding only allows A-Z0-9",
                    highlight_pattern = self.value,
                    highlight_sub=not_allowed_chars
            )
        return self
              
    def _value_to_python_type(self) -> bytes:
        decoded = bytes(from_base36(self))
        return decoded
    
    
class ErrorValue(Value):
    @field_validator('value', mode='before')
    @classmethod
    def _from_python_type(cls, v:str):
        return v
    
    @model_validator(mode='after')
    def _validate(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.value)):
            self._add_validation_message(
                    source=f"TREX value {self.value}",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Characters {_quote_texts(not_allowed_chars)} are not allowed in error segment",
                    highlight_pattern = self.value,
                    highlight_sub=not_allowed_chars
            )
        return self
       
    
    def _value_to_python_type(self) -> str:
        return self.value


class TREX_Segment(LabFREED_BaseModel, ABC):
    '''@private
    Abstract class representing a TREX_Segment
    '''
    key: str
    
    @abstractmethod
    def serialize(self):
        raise NotImplementedError("Subclasses must implement 'serialize_as_trex()' method")
    
    
    @model_validator(mode='after')
    def _validate_key(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.key)):
            self._add_validation_message(
                source=f"TREX segment key {self.key}",
                level=ValidationMsgLevel.ERROR,
                msg=f"Segment key contains invalid characters: {_quote_texts(not_allowed_chars)}",
                highlight_pattern = f'{self.key}$',
                highlight_sub=not_allowed_chars
            )
        return self
    

        
      
 
def str_to_value_type(s:str, t:str):
    match t:
        case 'T.D': 
            v = DateValue(value=s)
        case 'T.B': 
            v = BoolValue(value=s)
        case 'T.A': 
            v = AlphanumericValue(value=s)
        case 'T.T': 
            try:
                value = base36(s)
            except ValueError:
                logging.error('String given as T.T contains characters which base36 should not')
                value = s
            v = TextValue(value=value)
        case 'T.X': 
            v = BinaryValue(value=s)
        case 'E'  : 
            v = ErrorValue(value=s)
        case _    : 
            v = NumericValue(value=s)         
    return v   
    

    



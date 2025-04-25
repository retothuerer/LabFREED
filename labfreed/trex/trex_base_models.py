from datetime import date, datetime, time
import logging
import re



from pydantic import PrivateAttr, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel, _quote_texts
from abc import ABC, abstractmethod



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
        
        
        
class NumericValue(Value):
        
    @model_validator(mode='after')
    def _validate(self):
        value = self.value
        if not_allowed_chars := set(re.sub(r'[0-9\.\-E]', '', value)):
            self._add_validation_message(
                source=f"TREX numeric value {value}",
                level=ValidationMsgLevel.ERROR,
                msg=f"Characters {_quote_texts(not_allowed_chars)} are not allowed in quantity segment. Must be a number.",
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

class DateValue(Value):
    _date_time_dict:dict|None = PrivateAttr(default=None)
    
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
    

class BoolValue(Value):

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
                  
                    
class AlphanumericValue(Value):
        
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
             
    
class TextValue(Value):
        
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
                
    
class BinaryValue(Value):
        
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
                 
    
class ErrorValue(Value):
    
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
    

        



    



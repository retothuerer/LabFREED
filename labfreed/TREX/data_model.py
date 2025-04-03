from datetime import date, datetime, time
import logging
import re
from collections import Counter


from pydantic import ValidationError, field_validator, model_validator, Field
from labfreed.TREX.unece_units import unece_unit_codes
from labfreed.validation import BaseModelWithValidationMessages
from abc import ABC,  abstractmethod

from ..PAC_ID.data_model import Extension
from ..conversion_tools.utilities.base36 import to_base36, from_base36

        

class TREX_Segment(BaseModelWithValidationMessages, ABC):
    key: str
    
    @model_validator(mode='after')
    def validate_key(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.key)):
            self.add_validation_message(
                source=f"TREX segment key {self.key}",
                type="Error",
                msg=f"Segment name contains invalid characters: {','.join(not_allowed_chars)}",
                highlight_pattern = f'{self.key}$',
                highlight_sub=not_allowed_chars
            )
        return self
    
    @abstractmethod
    def serialize_for_trex(self):
        raise NotImplementedError("Subclasses must implement 'serialize_as_trex()' method")
    
    


class ValueMixin(BaseModelWithValidationMessages, ABC): 
    value:str 
        
    # @abstractclassmethod
    # def from_python_type(cls, v):
    #     ...
        
    # @abstractmethod
    # def to_python_type(self):
    #     ...
        
        
class NumericValue(ValueMixin):
    @model_validator(mode='after')
    def validate(self):
        value = self.value
        if not_allowed_chars := set(re.sub(r'[0-9\.-]', '', value)):
            self.add_validation_message(
                source=f"TREX numeric value {value}",
                type="Error",
                msg=f"Characters {','.join(not_allowed_chars)} are not allowed in quantity segment. Base36 encoding only allows A-Z0-9",
                highlight_pattern = f'{value}',
                highlight_sub=not_allowed_chars
            )
        if not re.fullmatch(r'-?\d+(\.\d+)?', value):
            self.add_validation_message(
                source=f"TREX numeric value {value}",
                type="Error",
                msg=f"{value} cannot be converted to number",
                highlight_pattern = f'{value}'               
            )
        return self
    


class DateValue(ValueMixin):
    @model_validator(mode='after')
    def validate(self):
        pattern:str = r'((?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}))?(T(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})?(\.(?P<millisecond>\d{3}))?)?'
        value=self.value
        if not re.fullmatch(pattern, value):
            self.add_validation_message(
                source=f"TREX date value {value}",
                type="Error",
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
        except ValueError as e:
            self.add_validation_message(
                source=f"TREX date value {value}",
                type="Error",
                msg=f'{value} is no valid date or time.',
                highlight_pattern = f'{value}'
            )
        
        return self
    
    def to_python_type(self) -> str:
        ...
    
    @classmethod
    def from_python_type(v:date|time|datetime):
        sd = ""
        st = ""
        match v:
            case date() | datetime():
                sd = v.strftime('%Y%m%d')
            case time() | datetime():
                if v.microsecond:
                    st = v.strftime("T%H:%M:%S.") + f"{v.microsecond // 1000:03d}"
                elif v.seconds:
                    st = v.strftime("T%H:%M:%S")
                else:
                    st = v.strftime("T%H:%M")
                         
        return DateValue(value= sd + st)
    

class BoolValue(ValueMixin):
    @model_validator(mode='after')
    def validate(self):
        if not self.value in ['T', 'F']:
            self.add_validation_message(
                source=f"TREX boolean value {self.value}",
                type="Error",
                msg=f'{self.value} is no valid boolean. Must be T or F',
                highlight_pattern = f':{self.value}',
                highlight_sub=[c for c in self.value]
            )
        return self
    
    def to_python_type(self) -> str:
        if self == 'T':
            return True
        elif self == 'F':
            return False
        else:
            Exception(f'{self} is not valid boolean. That really should not have been possible -- Contact the maintainers of the library')
            
          
class AlphanumericValue(ValueMixin):
    @model_validator(mode='after')
    def validate(self):
        if re.match(r'[a-z]', self.value):
            self.add_validation_message(
                    source=f"TREX value {self.value}",
                    type="Error",
                    msg=f"Lower case characters are not allowed.",
                    highlight_pattern = self.value
            )
            
        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.value)):
            self.add_validation_message(
                    source=f"TREX value {self.value}",
                    type="Error",
                    msg=f"Characters {','.join(not_allowed_chars)} are not allowed in alphanumeric segment",
                    highlight_pattern = self.value,
                    highlight_sub=not_allowed_chars
            )
        return self
           
    def to_python_type(self) -> str:
        return self
    
    @classmethod
    def from_python_type(cls, v):
        raise NotImplementedError()
    

class TextValue(ValueMixin):
    @model_validator(mode='after')
    def validate(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9]', '', self.value)):
            self.add_validation_message(
                    source=f"TREX value {self.value}",
                    type="Error",
                    msg=f"Characters {','.join(not_allowed_chars)} are not allowed in text segment. Base36 encoding only allows A-Z0-9",
                    highlight_pattern = self.value,
                    highlight_sub=not_allowed_chars
            )
        return self
              
    def to_python_type(self) -> str:
        decoded = from_base36(self)
        return decoded
    
    
class BinaryValue(ValueMixin):
    @model_validator(mode='after')
    def validate(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9]', '', self.value)):
           self.add_validation_message(
                    source=f"TREX value {self.value}",
                    type="Error",
                    msg=f"Characters {','.join(not_allowed_chars)} are not allowed in text segment. Base36 encoding only allows A-Z0-9",
                    highlight_pattern = self.value,
                    highlight_sub=not_allowed_chars
            )
        return self
              
    def to_python_type(self) -> bytes:
        decoded = bytes(from_base36(self))
        return decoded
    
    
class ErrorValue(ValueMixin):
    @model_validator(mode='after')
    def validate(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.value)):
            self.add_validation_message(
                    source=f"TREX value {self.value}",
                    type="Error",
                    msg=f"Characters {','.join(not_allowed_chars)} are not allowed in error segment",
                    highlight_pattern = self.value,
                    highlight_sub=not_allowed_chars
            )
        return self
       
    
    def to_python_type(self) -> str:
        return self



        
class ValueSegment(TREX_Segment, ValueMixin, ABC):
    type:str
    
    @classmethod
    def get_subclass(cls, type:str, key:str, value:str):
        match type:
            case 'T.D':
                model = DateSegment(key=key, value=value, type=type)
            case 'T.B':
                model = BoolSegment(key=key, value=value, type=type)
            case 'T.A':
                model = AlphanumericSegment(key=key, value=value, type=type)
            case 'T.T':
                model = TextSegment(key=key, value=value, type=type)
            case 'T.X':
                model = BinarySegment(key=key, value=value, type=type)
            case 'E':
                model = ErrorSegment(key=key, value=value, type=type)
            case _:
                if not type in unece_unit_codes():
                    raise ValueError(f'Invalid unit code. {type} is not in UNECE list of common codes')
                model = NumericSegment(value=value, key=key, type=type)
                    
        return model    
    
    
    def serialize_for_trex(self) -> str:
        return f'{self.key}${self.type}:{self.value}'
    

    
class NumericSegment(ValueSegment, NumericValue):
    type: str    
    
class DateSegment(ValueSegment, DateValue):
    type: str = Field('T.D', frozen=True)
    
class BoolSegment(ValueSegment, BoolValue):
    type: str = Field('T.A', frozen=True) 
        
class AlphanumericSegment(ValueSegment, AlphanumericValue):
    type: str = Field('T.A', frozen=True)
    
class TextSegment(ValueSegment, TextValue):
    type: str = Field('T.T', frozen=True)
    
class BinarySegment(ValueSegment, BinaryValue):
    type: str = Field('T.X', frozen=True)
    
class ErrorSegment(ValueSegment, ErrorValue):
    type: str = Field('E', frozen=True)
                        
        
    
class ColumnHeader(BaseModelWithValidationMessages):
    key:str
    type:str


  
class TREX_Table(TREX_Segment):
    col_headers: list[ColumnHeader]

    data: list[list[ValueMixin]]
    
    @model_validator(mode='after')
    def validate_sizes(self):
        
        sizes = [len(self.col_headers)]
        sizes.extend( [ len(row) for row in self.data ] ) 
        most_common_len, count = Counter(sizes).most_common(1)[0]        
        
        if len(self.col_headers) != most_common_len:
            self.add_validation_message(
                    source=f"Table {self.key}",
                    type="Error",
                    msg=f"Size mismatch: Table header contains {self.col_names} keys, while most rows have {most_common_len}",
                    highlight_pattern = self.key
            )
            expected_row_len = most_common_len
        else:
            expected_row_len = len(self.col_headers)
            

        for i, row in enumerate(self.data):
            if len(row) != expected_row_len:
                self.add_validation_message(
                    source=f"Table {self.key}",
                    type="Error",
                    msg=f"Size mismatch: Table row {i} contains {len(row)} elements. Expected size is {expected_row_len}",
                    highlight_pattern = self.key
                )

        
    def n_rows(self) -> int:
        return len(self.data)
    
    def n_cols(self) -> int:
        return len(self.col_names)
      
    def row_data(self, row:int) -> list:
        out = self.data[row]
        return out
                
    def col_data(self, col:str|int) -> list:
        col_index = self._get_col_index(col)
        type = self.col_types[col_index]
        out =  [row[col_index] for row in self.data]
        return out
     
    def cell_data(self, row:int, col:str|int):
        try:
            col_index = self._get_col_index(col)
            value = self.data[row][col_index]
        except ValueError:
            logging.warning(f"row {row}, column {col} not found")
            return None 
        return value
            
    def _get_col_index(self, col:str|int):
        if isinstance(col, str):
            col_index = self.col_names.index(col)
        elif isinstance(col, int):
            col_index = col
        else:
            raise TypeError(f"Column must be specified as string or int: {col.__name__}")
        return col_index
    
    
    
    def serialize_for_trex(self, name):
        header = ':'.join([f'{el[0]}${el[1]}' for el in zip(self.col_names, self.col_types)])
        date_rows = list()
        for r in self.data:
            row = ':'.join([cell.serialize_for_trex() for cell in r])
            date_rows.append(row)
        data = '::'.join(date_rows)
        s = f'{name}$${header}::{data}'
        return s
        
   



class TREX(Extension, BaseModelWithValidationMessages):
    name_:str
    segments: list[TREX_Segment] = Field(default_factory=list)
       
    @property
    def name(self)->str:
        return self.name_
    
    @property
    def type(self)->str:
        return 'TREX'
    
    @property
    def data(self)->str:
        seg_strings = list()
        for s in self.segments:
            seg_strings.append(s.serialize_for_trex())
        s_out = '+'.join(seg_strings)
        return s_out
    
    
    def get_segment(self, segment_key:str) -> TREX_Segment:
        s = [s for s in self.segments if s.key == segment_key]
        if s:
            return s[0]
        else:
            return None
        
        
    @field_validator('segments')
    @classmethod
    def validate_segments(cls, segments):
        segment_keys = [s.key for s in segments]
        duplicates = [item for item, count in Counter(segment_keys).items() if count > 1]
        if duplicates:
            raise ValueError(f"Duplicate segment keys: {','.join(duplicates)}")
        return segments
      
    
        
    @staticmethod
    def from_spec_fields(name, type, data):
        ...
    

    
class TREX_Struct(TREX_Segment):
    """Struct is a special interpretation of a T-REX Table with one row"""
    wrapped_table:TREX_Table
    
    @property
    def segment_name_(self):
        return self.wrapped_table.key
    
    @field_validator('wrapped_table')
    def validate_table(table):
        if len(table.data) != 1:
            raise ValidationError("Too many input rows. Struct can only have one row")
        return table
                
    def get(self, key):
        return self.wrapped_table.cell_data(0, key)
    
    def keys(self):
        return self.wrapped_table.col_names
    
    
    





          
# class Value(str, ABC): 
#     @classmethod
#     def __get_validators__(cls):
#         yield cls.validate
        
#     def __new__(cls, value):
#         # validate manually
#         validated = cls.validate(value)
#         return super().__new__(cls, validated)
        
#     @abstractclassmethod
#     def validate(cls, value):
#         ...
        
#     @abstractclassmethod
#     def from_python_type(v):
#         ...
        
#     @abstractmethod
#     def to_python_type():
#         ...
          
          
        
# class NumericValue(Value):
#     @classmethod
#     def validate(cls, value):
#         if not_allowed_chars := set(re.sub(r'[0-9\.-]', '', value)):
#             raise ValueError(f"Characters {','.join(not_allowed_chars)} are not allowed in quantity segment. Base36 encoding only allows A-Z0-9")
#         if not re.fullmatch(r'-?\d+(\.\d+)?', value):
#             raise ValueError(f"{value} cannot be converted to number")
#         return value
    
#     def to_python_type(self) -> str:
#         ...
        
# class DateValue(Value):
#     pattern = r'((?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}))?(T(?P<hours>\d{2})(?P<minutes>\d{2})(?P<seconds>\d{2})?(\.(?P<milliseconds>\d{3}))?)?'

#     @classmethod
#     def validate(cls, value):
#         if not re.fullmatch(cls.pattern, value):
#             raise ValueError(f'{value} is no valid date or time.')
#         return value
    
#     def to_python_type(self) -> str:
#         ...
    
#     @classmethod
#     def from_python_type(v:date|time|datetime):
#         sd = ""
#         st = ""
#         match v:
#             case date() | datetime():
#                 sd = v.strftime('%Y%m%d')
#             case time() | datetime():
#                 if v.microsecond:
#                     st = v.strftime("T%H:%M:%S.") + f"{v.microsecond // 1000:03d}"
#                 elif v.seconds:
#                     st = v.strftime("T%H:%M:%S")
#                 else:
#                     st = v.strftime("T%H:%M")
                         
#         return DateValue(sd + st)
    

          
          
# class BoolValue(Value):
#     @classmethod
#     def validate(cls, value):
#         if not value in ['T', 'F']:
#             raise ValueError(f'{value} is no valid boolean. Must be T or F')
#         return value
    
#     def to_python_type(self) -> str:
#         if self == 'T':
#             return True
#         elif self == 'F':
#             return False
#         else:
#             Exception(f'{self} is not valid boolean. That really should not have been possible -- Contact the maintainers of the library')
            
          
# class AlphanumericValue(Value):
#     @classmethod
#     def validate(cls, value):
#        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', value)):
#             raise ValueError(f"Characters {','.join(not_allowed_chars)} are not allowed in alphanumeric segment")
#        else:
#            return value
       
#     @property
#     def trex_type(self):
#         return 'T.A'
    
#     def to_python_type(self) -> str:
#         return self
    

# class TextValue(Value):

#     @classmethod
#     def validate(cls, value):
#        if not_allowed_chars := set(re.sub(r'[A-Z0-9]', '', value)):
#             raise ValueError(f"Characters {','.join(not_allowed_chars)} are not allowed in text segment. Base36 encoding only allows A-Z0-9")
#        else:
#            return value
       
#     @property
#     def trex_type(self):
#         return 'T.A'
       
#     def to_python_type(self) -> str:
#         decoded = from_base36(self)
#         return decoded
    
    
# class BinaryValue(Value):
#     @classmethod
#     def validate(cls, value):
#        if not_allowed_chars := set(re.sub(r'[A-Z0-9]', '', value)):
#             raise ValueError(f"Characters {','.join(not_allowed_chars)} are not allowed in text segment. Base36 encoding only allows A-Z0-9")
#        else:
#            return value
       
#     @property
#     def trex_type(self):
#         return 'T.X'
       
#     def to_python_type(self) -> bytes:
#         decoded = bytes(from_base36(self))
#         return decoded
    
    
# class ErrorValue(Value):
#     @classmethod
#     def validate(cls, value):
#        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', value)):
#             raise ValueError(f"Characters {','.join(not_allowed_chars)} are not allowed in error segment")
#        else:
#            return value
       
#     @property
#     def trex_type(self):
#         return 'E'
    
#     def to_python_type(self) -> str:
#         return self


# class TREX_Segment(BaseModelWithValidationMessages, ABC):
#     key: str
    
#     @field_validator('key')
#     def validate_name(cls, v):
#         if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', v)):
#             raise ValueError(f"Segment name contains invalid characters: {','.join(not_allowed_chars)}")
#         return v
    
#     @abstractmethod
#     def serialize_for_trex(self):
#         raise NotImplementedError("Subclasses must implement 'serialize_as_trex()' method")
    
    
    
# class ValueSegment(TREX_Segment):
#     type: str
#     value: str #NumericValue|DateValue|BoolValue|AlphanumericValue|TextValue|BinaryValue|ErrorValue
          
#     @model_validator(mode='before')
#     @classmethod
#     def validate(cls, model):
#         t = model.get('type')
#         v = model.get('value')
#         match t:
#             case 'T.D':
#                 v = DateValue(v)
#             case 'T.B':
#                 v = BoolValue(v)
#             case 'T.A':
#                 v = AlphanumericValue(v)
#             case 'T.T':
#                 v = TextValue(v)
#             case 'T.X':
#                 v = BinaryValue(v)
#             case 'E':
#                 v = ErrorValue(v)
#             case _:
#                 if not t in unece_unit_codes():
#                     raise ValueError(f'Invalid unit code. {t} is not in UNECE list of common codes')
#                 v = NumericValue(v)
                
#         model['value'] = v
#         return model
                
        
#     def serialize_for_trex(self) -> str:
#         return f'{self.key}${self.type}:{self.value}'
        
        # class UNECEQuantity(BaseModelWithWarnings):
#     value:int|float
#     unece_code:str
#     unit_name: str|None = ""
#     unit_symbol: str|None = ""
    
      
#     def as_strings(self):
#         unit_symbol = self.unit_symbol
#         if unit_symbol == "dimensionless":
#             unit_symbol = ""
#         s = ''

#         val_str = self.value
#         return f"{val_str}", f"{unit_symbol}", f"{val_str} {unit_symbol}"
        
#     def __str__(self):
#         unit_symbol = self.unit_symbol
#         if unit_symbol == "dimensionless":
#             unit_symbol = ""
        
#         s = f"{self.value} {unit_symbol}" 
#         return s




# class ValueSegment2(TREX_Segment, ValueMixin, ABC):
#     type:str
    
    # @model_validator(mode='before')
    # @classmethod
    # def convert_str_value(cls, model):
    #     if isinstance(model.get('value'), str):
    #         bases = [base for base in cls.__bases__ if base is not ValueSegment2 and issubclass(base, ValueMixin)]
    #         base = bases[0]
    #         v = base(value = model.get('value'))
    #         model['value'] = v
    #     return model
    
    
    # @model_validator(mode='before')
    # @classmethod
    # def cast_to_subclass(cls, model):
        
    #     # this method should do anything if called by the subclasses
    #     if cls is not ValueSegment2:
    #         return model
        
    #     k = model.get('key')
    #     t = model.get('type')
    #     v = model.get('value')      
    #     match t:
    #         case 'T.D':
    #             model = DateSegment(key=k, value=v, type=t)
    #         case 'T.B':
    #             model = BoolSegment(key=k, value=v, type=t)
    #         case 'T.A':
    #             model = AlphanumericSegment(key=k, value=v, type=t)
    #         case 'T.T':
    #             model = TextSegment(key=k, value=v, type=t)
    #         case 'T.X':
    #             model = BinarySegment(key=k, value=v, type=t)
    #         case 'E':
    #             model = ErrorSegment(key=k, value=v, type=t)
    #         case _:
    #             if not t in unece_unit_codes():
    #                 raise ValueError(f'Invalid unit code. {t} is not in UNECE list of common codes')
    #             model = NumericSegment(key=k, value=v, type=t)
                    
    #     return model    
    
    
    # class ValueSegment(TREX_Segment, ValueMixin, ABC):
    # type:str
    
    # @model_validator(mode='before')
    # @classmethod
    # def convert_str_value(cls, model):
    #     if isinstance(model.get('value'), str):
    #         bases = [base for base in cls.__bases__ if base is not ValueSegment2 and issubclass(base, ValueMixin)]
    #         base = bases[0]
    #         v = base(value = model.get('value'))
    #         model['value'] = v
    #     return model
    
    
    # @model_validator(mode='before')
    # @classmethod
    # def cast_to_subclass(cls, model):
        
    #     # this method should do anything if called by the subclasses
    #     if cls is not ValueSegment2:
    #         return model
        
    #     k = model.get('key')
    #     t = model.get('type')
    #     v = model.get('value')      
    #     match t:
    #         case 'T.D':
    #             model = DateSegment(key=k, value=v, type=t)
    #         case 'T.B':
    #             model = BoolSegment(key=k, value=v, type=t)
    #         case 'T.A':
    #             model = AlphanumericSegment(key=k, value=v, type=t)
    #         case 'T.T':
    #             model = TextSegment(key=k, value=v, type=t)
    #         case 'T.X':
    #             model = BinarySegment(key=k, value=v, type=t)
    #         case 'E':
    #             model = ErrorSegment(key=k, value=v, type=t)
    #         case _:
    #             if not t in unece_unit_codes():
    #                 raise ValueError(f'Invalid unit code. {t} is not in UNECE list of common codes')
    #             model = NumericSegment(key=k, value=v, type=t)
                    
    #     return model    
from datetime import date, datetime, time
import logging
import re
from collections import Counter
from typing import Annotated, Literal


from pydantic import PrivateAttr, RootModel, ValidationError, field_validator, model_validator, Field
from labfreed.TREX.unece_units import unece_unit, unece_unit_codes, unece_units, unit_name, unit_symbol
from labfreed.utilities.utility_types import DataTable, Quantity, Unit, unece_unit_code_from_quantity
from labfreed.validation import BaseModelWithValidationMessages
from abc import ABC,  abstractmethod

from labfreed.PAC_ID.extensions import Extension
from labfreed.utilities.base36 import base36, to_base36, from_base36

        

class TREX_Segment(BaseModelWithValidationMessages, ABC):
    key: str
    
    @model_validator(mode='after')
    def validate_key(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.key)):
            self.add_validation_message(
                source=f"TREX segment key {self.key}",
                type="Error",
                msg=f"Segment key contains invalid characters: {','.join(not_allowed_chars)}",
                highlight_pattern = f'{self.key}$',
                highlight_sub=not_allowed_chars
            )
        return self
    
    @abstractmethod
    def serialize_for_trex(self):
        raise NotImplementedError("Subclasses must implement 'serialize_as_trex()' method")
    
    # @abstractmethod
    # def to_python_type(self):
    #      raise NotImplementedError("Subclasses must implement 'to_python_type()' method")
     
    # @abstractmethod
    # def from_python_type(self):
    #      raise NotImplementedError("Subclasses must implement 'from_python_type()' method")
    
    


class ValueMixin(BaseModelWithValidationMessages, ABC): 
    value:str 
    
    def serialize_for_trex(self):
        return self.value
        
    # @abstractclassmethod
    # def from_python_type(cls, v):
    #     ...
        
    @abstractmethod
    def value_to_python_type(self):
        ...
        
        
class NumericValue(ValueMixin):
    @field_validator('value', mode='before')
    @classmethod
    def from_python_type(cls, v:str| int|float):
        if isinstance(v, str):
            return v
        return str(v)
        
    @model_validator(mode='after')
    def validate(self):
        value = self.value
        if not_allowed_chars := set(re.sub(r'[0-9\.\-E]', '', value)):
            self.add_validation_message(
                source=f"TREX numeric value {value}",
                type="Error",
                msg=f"Characters {','.join(not_allowed_chars)} are not allowed in quantity segment. Base36 encoding only allows A-Z0-9",
                highlight_pattern = f'{value}',
                highlight_sub=not_allowed_chars
            )
        if not re.fullmatch(r'-?\d+(\.\d+)?(E-?\d+)?', value):
            self.add_validation_message(
                source=f"TREX numeric value {value}",
                type="Error",
                msg=f"{value} cannot be converted to number",
                highlight_pattern = f'{value}'               
            )
        return self
    
    def value_to_python_type(self) -> str:
        v = float(self.value)  
        if not '.' in self.value and not 'E' in self.value: 
            return int(v)
        else:
            return v


class DateValue(ValueMixin):
    _date_time_dict:dict|None = PrivateAttr(default=None)
    @field_validator('value', mode='before')
    @classmethod
    def from_python_type(cls, v:str| date|time|datetime):
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
            
        self._date_time_dict = d
        return self
    
    def value_to_python_type(self) -> str:
        d = self._date_time_dict
        if d.get('year') and d.get('hour'): # input is only a time
            return datetime(**d)
        elif d.get('year'):
            return date(**d)
        else:
            return time(**d)
    
   
    

class BoolValue(ValueMixin):
    @field_validator('value', mode='before')
    @classmethod
    def from_python_type(cls, v:str| bool):
        if isinstance(v, str):
            return v
        
        return 'T' if v else 'F'

    @model_validator(mode='after')
    def validate(self):
        if not self.value in ['T', 'F']:
            self.add_validation_message(
                source=f"TREX boolean value {self.value}",
                type="Error",
                msg=f'{self.value} is no valid boolean. Must be T or F',
                highlight_pattern = f'{self.value}',
                highlight_sub=[c for c in self.value]
            )
        return self
    
    def value_to_python_type(self) -> str:
        if self.value == 'T':
            return True
        elif self.value == 'F':
            return False
        else:
            Exception(f'{self} is not valid boolean. That really should not have been possible -- Contact the maintainers of the library')
            
          
class AlphanumericValue(ValueMixin):
    @field_validator('value', mode='before')
    @classmethod
    def from_python_type(cls, v:str):
        return v
        
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
           
    def value_to_python_type(self) -> str:
        return self.value
    
    

class TextValue(ValueMixin):
    @field_validator('value', mode='before')
    @classmethod
    def from_python_type(cls, v:base36|str):
        if isinstance(v, str):
            logging.info('Got str for text value > converting to base36')
            return to_base36(v).root
        else:
            return v.root
        
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
              
    def value_to_python_type(self) -> str:
        decoded = from_base36(self.value)
        return decoded
    
    
class BinaryValue(ValueMixin):
    @field_validator('value', mode='before')
    @classmethod
    def from_python_type(cls, v:base36|str):
        if isinstance(v, str):
            return v
        else:
            return v.root
        
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
              
    def value_to_python_type(self) -> bytes:
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
       
    
    def value_to_python_type(self) -> str:
        return self.value



        
class ValueSegment(TREX_Segment, ValueMixin, ABC):
    type:str
    
    @model_validator(mode='after')
    def validate_type(self):
        valid_types = valid_types = unece_unit_codes() + ['T.D', 'T.B', 'T.A', 'T.T', 'T.X', 'E']
        if not self.type in valid_types:
            self.add_validation_message(
                    source=f"TREX value segment {self.key}",
                    type="Error",
                    msg=f"Type {self.type} is invalid. Must be 'T.D', 'T.B', 'T.A', 'T.T', 'T.X', 'E' or a UNECE unit",
                    highlight_pattern = self.type
            )
        return self
    
    # @classmethod
    # def get_subclass(cls, type:str, key:str, value:str):
    #     match type:
    #         case 'T.D':
    #             model = DateSegment(key=key, value=value, type=type)
    #         case 'T.B':
    #             model = BoolSegment(key=key, value=value, type=type)
    #         case 'T.A':
    #             model = AlphanumericSegment(key=key, value=value, type=type)
    #         case 'T.T':
    #             model = TextSegment(key=key, value=value, type=type)
    #         case 'T.X':
    #             model = BinarySegment(key=key, value=value, type=type)
    #         case 'E':
    #             model = ErrorSegment(key=key, value=value, type=type)
    #         case _:
    #             model = NumericSegment(value=value, key=key, type=type)
                    
    #     return model    
    
    
    def serialize_for_trex(self) -> str:
        return f'{self.key}${self.type}:{self.value}'
    
    def to_python_type(self):
        return self.value_to_python_type()
    
    

    
    

    
class NumericSegment(ValueSegment, NumericValue):
    type: str    
    
    def to_python_type(self):
        unit = unece_unit(self.type)
        out = Quantity(value=self.value_to_python_type(), unit=Unit(name=unit_name(unit), symbol=unit_symbol(unit)))
        return out
    
class DateSegment(ValueSegment, DateValue):
    type: Literal['T.D'] = Field('T.D', frozen=True)
          
class BoolSegment(ValueSegment, BoolValue):
    type: Literal['T.B']  = Field('T.B', frozen=True) 
        
class AlphanumericSegment(ValueSegment, AlphanumericValue):
    type: Literal['T.A'] = Field('T.A', frozen=True)
    
class TextSegment(ValueSegment, TextValue):
    type: Literal['T.T'] = Field('T.T', frozen=True)
    
class BinarySegment(ValueSegment, BinaryValue):
    type: Literal['T.X'] = Field('T.X', frozen=True)
    
class ErrorSegment(ValueSegment, ErrorValue):
    type: Literal['E'] = Field('E', frozen=True)
                        
        
    
class ColumnHeader(BaseModelWithValidationMessages):
    key:str
    type:str
               
    @model_validator(mode='after')     
    def validate_key(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.key)):
            self.add_validation_message(
                source=f"TREX table column {self.key}",
                type="Error",
                msg=f"Column header key contains invalid characters: {','.join(not_allowed_chars)}",
                highlight_pattern = f'{self.key}$',
                highlight_sub=not_allowed_chars
            )
        return self
    
    @model_validator(mode='after')
    def validate_type(self):
        valid_types = unece_unit_codes() + ['T.D', 'T.B', 'T.A', 'T.T', 'T.X', 'E']
        if not self.type in valid_types:
            self.add_validation_message(
                    source=f"TREX table column {self.key}",
                    type="Error",
                    msg=f"Type '{self.type}' is invalid. Must be 'T.D', 'T.B', 'T.A', 'T.T', 'T.X', 'E' or a UNECE unit",
                    highlight_pattern = self.type
            )
        return self

class TableRow(RootModel[list[ValueMixin]]):    
    def serialize_for_trex(self):
        return ':'.join([e.serialize_for_trex() for e in self.root])
    
    def __len__(self):
        return len(self.root)
    
    def __iter__(self):
        return iter(self.root)
  
class TREX_Table(TREX_Segment):
    column_headers: list[ColumnHeader]
    data: list[TableRow]
    
    @property
    def column_names(self):
        return [h.key for h in self.column_headers]
    
    @property
    def column_types(self):
        return [h.type for h in self.column_headers]
    
    @model_validator(mode='after')
    def validate_sizes(self):
        sizes = [len(self.column_headers)]
        sizes.extend( [ len(row) for row in self.data ] ) 
        most_common_len, count = Counter(sizes).most_common(1)[0]        
        
        if len(self.column_headers) != most_common_len:
            self.add_validation_message(
                    source=f"Table {self.key}",
                    type="Error",
                    msg=f"Size mismatch: Table header contains {self.column_names} keys, while most rows have {most_common_len}",
                    highlight_pattern = self.key
            )
            expected_row_len = most_common_len
        else:
            expected_row_len = len(self.column_headers)
            

        for i, row in enumerate(self.data):
            if len(row) != expected_row_len:
                self.add_validation_message(
                    source=f"Table {self.key}",
                    type="Error",
                    msg=f"Size mismatch: Table row {i} contains {len(row)} elements. Expected size is {expected_row_len}",
                    highlight_pattern = row.serialize_for_trex()
                )
        return self
    
    @model_validator(mode='after')
    def validate_data_types(self):
        expected_types = self.column_types
        i = 0
        for row in self.data:
            for e, t_expected, nm in zip(row, expected_types, self.column_names):
                try:
                    match t_expected:
                        case 'T.D':
                            assert isinstance(e, DateValue)
                        case 'T.B':
                            assert isinstance(e, BoolValue)
                        case 'T.A':
                            assert isinstance(e, AlphanumericValue)
                            
                        case 'T.T':
                            assert isinstance(e, TextValue)
                        case 'T.X':
                            assert isinstance(e, BinaryValue)
                        case 'E':
                            assert isinstance(e, ErrorValue)
                        case _:
                            assert isinstance(e, NumericValue)
                except AssertionError:
                    self.add_validation_message(
                        source=f"Table {self.key}",
                        type="Error",
                        msg=f"Type mismatch: Table row {i}, column {nm} is of wrong type. According to the header it should be {t_expected}",
                        highlight_pattern = row.serialize_for_trex(),
                        highlight_sub=[c for c in e.value]
                    )
                    
                if msg := e.get_errors():
                    for m in msg:
                        self.add_validation_message(
                            source=f"Table {self.key}",
                            type="Error",
                            msg=m.problem_msg,
                            highlight_pattern = row.serialize_for_trex(),
                            highlight_sub=[c for c in e.value]
                        )
                i += 1
                
            
    def _get_col_index(self, col:str|int):
        if isinstance(col, str):
            col_index = self.column_names.index(col)
        elif isinstance(col, int):
            col_index = col
        else:
            raise TypeError(f"Column must be specified as string or int: {col.__name__}")
        return col_index
    
    
    
    def serialize_for_trex(self):
        header = ':'.join([f'{h.key}${h.type}' for h in self.column_headers])        
        data = '::'.join([r.serialize_for_trex() for r in self.data])
        s = f'{self.key}$${header}::{data}'
        return s
    
    
    def to_python_type(self):
        table = DataTable([ch.key for ch in self.column_headers])
        for row in self.data:
            r = []
            for e, h in zip(row, self.column_headers):
                if isinstance(e, NumericValue):
                    u = unece_unit(h.type)
                    unit = Unit(name=u.get('name'), symbol=u.get('symbol'))
                    r.append(Quantity(value=e.value, unit=unit))
                else:
                    r.append(e.value_to_python_type())
            table.append(r)
        return table
        
        
        
    def n_rows(self) -> int:
        return len(self.data)
    
    def n_cols(self) -> int:
        return len(self.column_headers)
      
    def row_data(self, row:int) -> list:
        out = self.data[row]
        return out
    
    
    def column_data(self, col:str|int) -> list:
        col_index = self._get_col_index(col)
        type = self.column_headers[col_index].type
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
        
        
    def update(self, segments: dict[str, Quantity|datetime|time|date|bool|str|base36|DataTable] ):
        for k, v in segments.items():
            if isinstance(v, bool):
                self.segments.append(BoolSegment(key=k, value=v))
            elif isinstance(v, Quantity):
                unece_code = unece_unit_code_from_quantity(v)
                self.segments.append(NumericSegment(key=k, value=v.value, type=unece_code))
            elif isinstance(v, (int, float)):
                self.segments.append(NumericSegment(key=k, value=v, type='C63'))  # unitless
            elif isinstance(v, (datetime, time, date)):
                self.segments.append(DateSegment(key=k, value=v))
            elif isinstance(v, str):
                if re.fullmatch(r'[A-Z0-9\-\.]*', v):
                    self.segments.append(AlphanumericSegment(key=k, value=v))
                else:
                    v = to_base36(v)
                    self.segments.append(TextSegment(key=k, value=v))
            elif isinstance(v, base36):
                self.segments.append(TextSegment(key=k, value=v))
            elif isinstance(v, DataTable):
                v:DataTable = v
                headers = list()
                for nm, rt in zip(v.col_names, v.row_template):
                    if isinstance(rt, bool): # must come first otherwise int matches the bool
                        t = 'T.B'
                    elif isinstance(rt, Quantity):
                        unece_code = unece_unit_code_from_quantity(rt)
                        t = unece_code
                    elif isinstance(rt, (datetime, time, date)):
                        t = 'T.D'     
                    elif isinstance(rt, str):
                        if re.fullmatch(r'[A-Z0-9\-\.]*', rt):
                            t = 'T.A'
                        else:
                            v = to_base36(rt)
                            t = 'T.X'
                    elif isinstance(rt, base36):
                        t = 'T.X'
                    
                    headers.append(ColumnHeader(key=nm, type=t))
                data = []
                for row in v:
                    r = []
                    for e in row:
                        if isinstance(e, bool): # must come first otherwise int matches the bool
                            r.append(BoolValue(value=e))
                        elif isinstance(e, Quantity):
                            r.append(NumericValue(value=e.value))
                        elif isinstance(e, (int, float)):
                            r.append(NumericValue(value=e))
                        elif isinstance(e, (datetime, time, date)):
                            r.append(DateValue(value=e))
                        elif isinstance(e, str):
                            if re.fullmatch(r'[A-Z0-9\-\.]*', e):
                                r.append(AlphanumericValue(value=e))
                            else:
                                e = to_base36(e)
                                r.append(TextValue(value=e))
                        elif isinstance(e, base36):
                            r.append(TextValue(value=e))
                    data.append(r)
                    
                self.segments.append(TREX_Table(key=k, column_headers=headers, data=data))
        return self
                   
                
    def dict(self):
        return {s.key: s.to_python_type() for s in self.segments}
            
        
        
    @field_validator('segments')
    @classmethod
    def validate_segments(cls, segments):
        segment_keys = [s.key for s in segments]
        duplicates = [item for item, count in Counter(segment_keys).items() if count > 1]
        if duplicates:
            raise ValueError(f"Duplicate segment keys: {','.join(duplicates)}")
        return segments
      
    
        
    @staticmethod
    def from_spec_fields(*, name, data, type='TREX'):
        segment_strings = data.split('+')
        out_segments = list()
        for s in segment_strings:
            # there are only two valid options. The segment is a scalar or a table. 
            # Constructors do the parsing anyways and raise exceptions if invalid data
            # try both options and then let it fail
            segment = _deserialize_table_segment_from_trex_segment_str(s)
            if not segment:
                segment = _deserialize_value_segment_from_trex_segment_str(s)
            if not segment:
                raise ValueError('TREX contains neither valid value segment nor table')
                
            out_segments.append(segment)
        trex = TREX(name_= name, segments=out_segments)
    
        return trex
    
    
def _deserialize_value_segment_from_trex_segment_str(trex_segment_str) -> ValueSegment:
    #re_scalar_pattern = re.compile(f"(?P<name>[\w\.-]*?)\$(?P<unit>[\w\.]*?):(?P<value>.*)")
    re_scalar_pattern = re.compile(f"(?P<name>.+?)\$(?P<unit>.+?):(?P<value>.+)")
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
            out = TextSegment(key=key, value=base36(value), type=type_)  # prevent repeated conversion from str to base36 and make explict that when parsing we assume the string tpo be base36 already
        case 'T.X':
            out = BinarySegment(key=key, value=base36(value), type=type_) # prevent repeated conversion from str to base36 and make explict that when parsing we assume the string tpo be base36 already
        case 'E':
            out = ErrorSegment(key=key, value=value, type=type_)
        case _:
            out = NumericSegment(value=value, key=key, type=type_)
                    
    return out    
    


def _deserialize_table_segment_from_trex_segment_str(trex_segment_str) -> TREX_Table:
    # re_table_pattern = re.compile(f"(?P<tablename>[\w\.-]*?)\$\$(?P<header>[\w\.,\$:]*?)::(?P<body>.*)")
    # re_col_head_pattern = re.compile(f"(?P<name>[\w\.-]*?)\$(?P<unit>[\w\.]*)")
    re_table_pattern = re.compile(r"(?P<tablename>.+?)\$\$(?P<header>.+?)::(?P<body>.+)")
    
    matches = re_table_pattern.match(trex_segment_str) 
    if not matches:
        return None
    name, header, body = matches.groups()
    
    column_headers_str = header.split(':')
    
    headers = []
    for colum_header in column_headers_str:
         ch = colum_header.split('$')
         col_key = ch[0]
         col_type = ch[1] if len(ch) > 1 else ''
         headers.append(ColumnHeader(key=col_key, type=col_type))
    
    data = [row.split(':') for row in body.split('::') ]
    col_types = [h.type for h in headers]
    # convert to correct value types
    data_with_types = [[str_to_value_type(c,t) for c, t in zip(r, col_types)] for r in data]
    data = [ TableRow(r) for r in data_with_types]
             
    out = TREX_Table(column_headers=headers, data=data_with_types, key=name)
    return out
        

def str_to_value_type(s:str, t:str):
    match t:
        case 'T.D': v = DateValue(value=s)
        case 'T.B': v = BoolValue(value=s)
        case 'T.A': v = AlphanumericValue(value=s)
        case 'T.T': v = TextValue(value=base36(s))
        case 'T.X': v = BinaryValue(value=s)
        case 'E'  : v = ErrorValue(value=s)
        case _    : v = NumericValue(value=s)         
    return v   
    

    
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
    
    
    



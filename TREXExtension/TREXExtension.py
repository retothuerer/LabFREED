from datetime import datetime
from enum import Enum
import logging
import re
from PAC_ID.PAC_ID import Extension
from pydantic import BaseModel, field_validator
from abc import ABC

from unit_utilities import PydanticUncertainQuantity, quantity_from_UN_CEFACT

re_table_pattern = re.compile(f"(?P<tablename>[\w\.-]*?)\$\$(?P<header>[\w\.,\$:]*?)::(?P<body>.*)")
re_col_head_pattern = re.compile(f"(?P<name>[\w\.-]*?)\$(?P<unit>[\w\.]*)")
re_scalar_pattern = re.compile(f"(?P<name>[\w\.-]*?)\$(?P<unit>[\w\.]*?):(?P<value>.*)")
        
TREX_DATEFORMAT = '%Y%m%dT%H%M%S'
TREX_TIMEFORMAT = '%Y%m%d'
        
class TREX_types(Enum):
    BOOL = 'T.B'
    DATE = 'T.D'
    TEXT = 'T.A'
    ERROR = 'E'
    

   
class T_REX_Segment_ParseError(BaseException):
    pass


class TREX_Segment(BaseModel, ABC):
    segment_name: str = None
    
    def as_trex_segment_str(self, segment_name):
        pass
 
      
class TREX_SimpleSegment(TREX_Segment):
    type: str 
    value: str
    
    @field_validator('type', mode='before')
    def validate_type(t):
        if isinstance(t, TREX_types):
            t = t.value
        return t
          
    @staticmethod
    def from_trex_segmentstring(segment_str):
       
        matches = re_scalar_pattern.match(segment_str)
        if not matches:
            raise T_REX_Segment_ParseError("Segment is not a valid TREX Scalar")
        
        name, type_, value = matches.groups()
        
        out = TREX_SimpleSegment(type=type_, value=value, segment_name=name)
        return out
        
    @property
    def value_as_builtin_or_quantity_type(self) -> datetime|bool|str|PydanticUncertainQuantity:
        return _value_as_builtin_or_quantity(self.value, self.type)
    
    def as_trex_segment_str(self, segment_name) -> str:
        return f'{segment_name}${self.type}:{self.value}'
  
  
class TREX_Table(TREX_Segment):
    col_names: list[str]
    col_types: list[str]
    data: list[list[str]]
        
    @staticmethod
    def from_trex_segmentstring( segment_str:str):
        matches = re_table_pattern.match(segment_str) 
        if not matches:
            raise T_REX_Segment_ParseError(f"Segment is not a valid TREX table: {segment_str}")
        name, header, body = matches.groups()
                
        column_heads = [re_col_head_pattern.match(colhead).groups() for colhead in header.split(':')]
        col_names = [ch[0] for ch in column_heads]
        col_types = [ch[1] for ch in column_heads]
        
        data = [row.split(':') for row in body.split('::') ]
        
        out = TREX_Table(col_names=col_names, col_types=col_types, data=data, segment_name=name)
        return out
     
    def n_rows(self) -> int:
        return len(self.data)
    
    def n_cols(self) -> int:
        return len(self.col_names)
      
    def row_data(self, row:int) -> list:
        out = [_value_as_builtin_or_quantity(element, self.col_types[i]) for i, element in enumerate(self.data)]
        return out
                
    def col_data(self, col:str|int) -> list:
        col_index = self._get_col_index(col)
        type = self.col_types[col_index]
        out =  [_value_as_builtin_or_quantity(row[col_index],type) for row in self.data]
        return out
     
    def cell_data(self, row:int, col:str|int):
        try:
            col_index = self._get_col_index(col)
            value = self.data[row][col_index]
            type = self.col_types[col_index]   
        except ValueError:
            logging.warning(f"row {row}, column {col} not found")
            return None
        
        return _value_as_builtin_or_quantity(value, type)
            
    def _get_col_index(self, col:str|int):
        if isinstance(col, str):
            col_index = self.col_names.index(col)
        elif isinstance(col, int):
            col_index = col
        else:
            raise TypeError(f"Column must be specified as string or int: {col.__name__}")
        return col_index
    
    def as_trex_segment_str(self, name):
        header = ':'.join([f'{el[0]}${el[1]}' for el in zip(self.col_names, self.col_types)])
        date_rows = list()
        for r in self.data:
            row = ':'.join([str(cell) for cell in r])
            date_rows.append(row)
        data = '::'.join(date_rows)
        s = f'{name}$${header}::{data}'
        return s
        


class TREX(Extension, BaseModel):
    _name:str
    segments: dict[str,TREX_Segment]
       
    @property
    def name(self)->str:
        return 'N'
    
    @property
    def type(self)->str:
        return 'N'
    
    @property
    def data(self)->str:
        seg_strings = list()
        for s_name, s in self.segments.items():
            seg_strings.append(s.as_trex_segment_str(s_name))
        s_out = '+'.join(seg_strings)
        return s_out
    
    @staticmethod
    def from_spec_fields(name, type, data):
        if type != 'TREX':
            logging.warning(f'Type {name} was given, but this extension should only be used with type "TREX". Will try to parse data as TREX')
        
        if not data:
            raise ValueError(f'T-REX must be a string of non zero length')
        
        trex_str = data

        # remove extension indicator. Precaution in case it is not done yet
        if trex_str[0]=="*":
            trex_str=trex_str[1:-1]
        # remove line breaks. for editing T-REXes it's more convenient to have them in, so one never knows 
        trex_str = trex_str.replace('\n','')
                
        segment_strings = trex_str.split('+')
        out_segments = dict()
        for s in segment_strings:
            # there are only two valid options. The segment is a scalar or a table. 
            # Constructors do the parsing anyways and raise exceptions if invalid data
            # try both options and then let it fail
            try:
                segment = TREX_SimpleSegment.from_trex_segmentstring(data)
            except T_REX_Segment_ParseError:
                segment = TREX_Table.from_trex_segmentstring(data)
            out_segments[segment.segment_name] = segment
        
        return TREX(_name=name, segments=out_segments)
    
 
def _to_datetime(trex_datetime):  
    try:
        # return datetime.fromisoformat(trex_datetime) # should work with python 3.11
        return datetime.strptime(trex_datetime, TREX_DATEFORMAT)
    except (ValueError , TypeError) as e:
        try:
            return datetime.strptime(trex_datetime, TREX_TIMEFORMAT)
        except (ValueError, TypeError):
            return None
        
def _value_as_builtin_or_quantity(v:str|list[str], type:str) -> datetime|bool|str|PydanticUncertainQuantity:
    match type:
        case 'T.D':
            return _to_datetime(v)
        case 'T.B':
            return v == 'T' or bool(v)
        case 'T.A':
            return v
        case 'T.X':
            raise NotImplementedError("Base36 encoded T-REX segment not implemented")
        case 'E':
            return v
        case _:
            return quantity_from_UN_CEFACT(v, type)
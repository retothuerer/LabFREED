       
    
from collections import Counter
import logging
import re

from pydantic import RootModel, model_validator
from labfreed.trex.trex_base_models import Value
from labfreed.well_known_keys.unece.unece_units import unece_unit_codes
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel, _quote_texts
from labfreed.trex.trex_base_models import AlphanumericValue, BinaryValue, BoolValue, DateValue, ErrorValue, NumericValue, TREX_Segment, TextValue


class ColumnHeader(LabFREED_BaseModel):
    '''Header of a table Column'''
    key:str
    type:str
               
    @model_validator(mode='after')     
    def _validate_key(self):
        if not_allowed_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.key)):
            self._add_validation_message(
                source=f"TREX table column {self.key}",
                level= ValidationMsgLevel.ERROR,
                msg=f"Column header key contains invalid characters: {_quote_texts(not_allowed_chars)}",
                highlight_pattern = f'{self.key}$',
                highlight_sub=not_allowed_chars
            )
        return self
    
    @model_validator(mode='after')
    def _validate_type(self):
        valid_types = unece_unit_codes() + ['T.D', 'T.B', 'T.A', 'T.T', 'T.X', 'E']
        if self.type not in valid_types:
            self._add_validation_message(
                    source=f"TREX table column {self.key}",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Type '{self.type}' is invalid. Must be 'T.D', 'T.B', 'T.A', 'T.T', 'T.X', 'E' or a UNECE unit",
                    highlight_pattern = self.type
            )
        return self

class TableRow(RootModel[list[Value]]):
    """
    Represents a row in a table.

    This class is a Pydantic RootModel that wraps a `list[ValueMixin]`.
    Each element in the list corresponds to a cell in the row.

    All common list operations (indexing, iteration, append, pop, etc.) are supported.
    Internally, it wraps a list in the `.root` attribute.
    """
    def serialize(self):
        return ':'.join([e.serialize() for e in self.root])
    
    def __len__(self):
        return len(self.root)
    
    def __iter__(self):
        return iter(self.root)
    
    def __repr__(self):
        return f"TableRow({self.root!r})  # wraps list[{Value.__name__}]"
    
  
class TableSegment(TREX_Segment):
    '''TREX Segment which represents tabular data'''
    key:str   
    column_headers: list[ColumnHeader]
    data: list[TableRow]
    
    @property
    def column_names(self):
        return [h.key for h in self.column_headers]
    
    @property
    def column_types(self):
        return [h.type for h in self.column_headers]
    
    @model_validator(mode='after')
    def _validate_sizes(self):
        sizes = [len(self.column_headers)]
        sizes.extend( [ len(row) for row in self.data ] ) 
        most_common_len, count = Counter(sizes).most_common(1)[0]        
        
        if len(self.column_headers) != most_common_len:
            self._add_validation_message(
                    source=f"Table {self.key}",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Size mismatch: Table header contains {self.column_names} keys, while most rows have {most_common_len}",
                    highlight_pattern = self.key
            )
            expected_row_len = most_common_len
        else:
            expected_row_len = len(self.column_headers)
            

        for i, row in enumerate(self.data):
            if len(row) != expected_row_len:
                self._add_validation_message(
                    source=f"Table {self.key}",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Size mismatch: Table row {i} contains {len(row)} elements. Expected size is {expected_row_len}",
                    highlight_pattern = row.serialize()
                )
        return self
    
    @model_validator(mode='after')
    def _validate_data_types(self):
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
                    self._add_validation_message(
                        source=f"Table {self.key}",
                        level= ValidationMsgLevel.ERROR,
                        msg=f"Type mismatch: Table row {i}, column {nm} is of wrong type. According to the header it should be {t_expected}",
                        highlight_pattern = row.serialize(),
                        highlight_sub=[c for c in e.value]
                    )
                    
                if msg := e.errors():
                    for m in msg:
                        self._add_validation_message(
                            source=f"Table {self.key}",
                            level= ValidationMsgLevel.ERROR,
                            msg=m.msg,
                            highlight_pattern = row.serialize(),
                            highlight_sub=[c for c in e.value]
                        )
                i += 1
        return self
                
            
    def _get_col_index(self, col:str|int):
        if isinstance(col, str):
            col_index = self.column_names.index(col)
        elif isinstance(col, int):
            col_index = col
        else:
            raise TypeError(f"Column must be specified as string or int: {col.__name__}")
        return col_index
    
    
    
    def serialize(self):
        header = ':'.join([f'{h.key}${h.type}' for h in self.column_headers])        
        data = '::'.join([r.serialize() for r in self.data])
        s = f'{self.key}$${header}::{data}'
        return s
    

    def n_rows(self) -> int:
        return len(self.data)
    
    def n_cols(self) -> int:
        return len(self.column_headers)
      
    def row_data(self, row:int) -> list:
        out = self.data[row]
        return out
    
    
    def column_data(self, col:str|int) -> list:
        col_index = self._get_col_index(col)
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
   



 

def _deserialize_table_segment_from_trex_segment_str(trex_segment_str) -> TableSegment:
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
    # convert to correct value types
    data_with_types = [[_str_to_value_type(h.type, cv) for cv, h in zip(r, headers)] for r in data]
    data = [ TableRow(r) for r in data_with_types]
             
    out = TableSegment(column_headers=headers, data=data, key=name)
    return out

def _str_to_value_type(type_, s):
    match type_:
        case 'T.D':
            out = DateValue(value=s)
        case 'T.B':
            out = BoolValue(value=s)
        case 'T.A':
            out = AlphanumericValue(value=s)
        case 'T.T':
            out = TextValue(value=s)
        case 'T.X':
            out = BinaryValue(value=s)
        case 'E':
            out = ErrorValue(value=s)
        case _:
            out = NumericValue(value=s)
    return out
        

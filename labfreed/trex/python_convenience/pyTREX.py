
from datetime import date, datetime, time
import logging
import re

from pydantic import RootModel
from labfreed.well_known_keys.unece.unece_units import unece_unit
from labfreed.trex.python_convenience.data_table import DataTable
from labfreed.utilities.base36 import from_base36, base36, to_base36

from labfreed.trex.python_convenience.quantity import Quantity, unece_unit_code_from_quantity
from labfreed.trex.table_segment import ColumnHeader, TableSegment
from labfreed.trex.trex import TREX
from labfreed.trex.trex_base_models import AlphanumericValue, BinaryValue, BoolValue, DateValue, ErrorValue, NumericValue, TextValue
from labfreed.trex.value_segments import BoolSegment, ErrorSegment, TextSegment, NumericSegment, AlphanumericSegment, DateSegment, ValueSegment


class pyTREX(RootModel[dict[str, Quantity | datetime | time | date | bool | str | base36 | DataTable]]):
    ''' A wrapper around dict, which knows how to convert to and from TREX. 
        It restricts the types allowed as values. Keys must be str.
    '''
    model_config = {'arbitrary_types_allowed':True} # needed to allow Quantity and DataTable w/o implementing the pydantic schema
    '''@private'''

    
    @classmethod
    def from_trex(cls, trex:TREX):
        '''Creates a pyTREX from a TREX'''
        return {seg.key: _trex_segment_to_python_type(seg) for seg in trex.segments}
             
             
    def to_trex(self):
        '''Creates a TREX'''
        segments = list()
        for k, v in self.root.items():
            if v is None:
                value = _error_value_from_python_type(v)
                segments.append(ErrorSegment(key=k, value=value.value))
            elif isinstance(v, bool):
                value = _bool_value_from_python_type(v)
                segments.append(BoolSegment(key=k, value=value.value))
            elif isinstance(v, Quantity):
                unece_code = unece_unit_code_from_quantity(v)
                value = _numeric_value_from_python_type(v.value)
                segments.append(NumericSegment(key=k, value=value.value, type=unece_code))
            elif isinstance(v, (int, float)):
                value = _numeric_value_from_python_type(v)
                segments.append(NumericSegment(key=k, value=value.value, type='C63'))  # unitless
            elif isinstance(v, (datetime, time, date)):
                value = _date_value_from_python_type(v)
                segments.append(DateSegment(key=k, value=value.value))
            elif isinstance(v, str):
                if re.fullmatch(r'[A-Z0-9\-\.]*', v):
                    value = _alphanumeric_value_from_python_type(v)
                    segments.append(AlphanumericSegment(key=k, value=value.value))
                else:
                    v = to_base36(v)
                    value = _text_value_from_python_type(v)
                    segments.append(TextSegment(key=k, value=value.value))
            elif isinstance(v, base36):
                value = _text_value_from_python_type(v)
                segments.append(TextSegment(key=k, value=value.value))
                
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
                for row in v.data:
                    r = []
                    for e in row:
                        if e is None:
                            r.append(_error_value_from_python_type(e))
                        elif isinstance(e, bool): # must come first otherwise int matches the bool
                            r.append(_bool_value_from_python_type(e))
                        elif isinstance(e, Quantity):
                            r.append(_numeric_value_from_python_type(e.value))
                        elif isinstance(e, (int, float)):
                            r.append(_numeric_value_from_python_type(e))
                        elif isinstance(e, (datetime, time, date)):
                            r.append(_date_value_from_python_type(e))
                        elif isinstance(e, str):
                            if re.fullmatch(r'[A-Z0-9\-\.]*', e):
                                r.append(_alphanumeric_value_from_python_type(e))
                            else:
                                e = to_base36(e)
                                r.append(_text_value_from_python_type(e))
                        elif isinstance(e, base36):
                            r.append(_text_value_from_python_type(e))
                    data.append(r)
                segments.append(TableSegment(key=k, column_headers=headers, data=data))
        return TREX(segments=segments)
    
    # make the usual dict methods available, for convenience
    def __getitem__(self, key): return self.root[key]
    def __setitem__(self, key, value): self.root[key] = value
    def update(self, *args, **kwargs):
        return self.root.update(*args, **kwargs)
    def keys(self): return self.root.keys()
    def values(self): return self.root.values()
    def items(self): return self.root.items()
    def __contains__(self, key): return key in self.root
    def __iter__(self): return iter(self.root)
    def __len__(self): return len(self.root)
    
  
  
# Helper functions to convert python types to TREX types    

def _numeric_value_from_python_type(v:int|float):
    return NumericValue(value = str(v))


def _date_value_from_python_type(v:date|time|datetime):    
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
                        
    return DateValue(value = sd + st)
    
    
def _bool_value_from_python_type(v:bool):
    return BoolValue(value = 'T' if v else 'F')


def _alphanumeric_value_from_python_type(v:str):
    return AlphanumericValue(value = v)


def _text_value_from_python_type(v:base36|str):
    if isinstance(v, str):
        logging.info('Got str for text value > converting to base36')
        out =  to_base36(v).root
    else:
        out =  v.root
    return TextValue(value = out)
        
        
def _binary_value_from_python_type(v:base36|str):
    if isinstance(v, str):
        out = v
    else:
        out = v.root
    return BinaryValue(value = out)
    

def _error_value_from_python_type(v:str):
    if v in None:
        v = '-'
    return ErrorValue(value = v)
    


# Helper functions to convert from TREX types to python types
def _trex_segment_to_python_type(v):
    '''Converts a TREX segment to a python value. Note the segment key must be handles outside.'''
    if isinstance(v, NumericSegment):
        num_val = _trex_value_to_python_type(v)
        u = unece_unit(v.type)
        unit = u.get('symbol')
        return Quantity(value=num_val, unit=unit)
    
    # value segments are derived from their respective value type
    elif isinstance(v, ValueSegment):
        return _trex_value_to_python_type(v)

    elif isinstance(v, TableSegment):
        table = DataTable(col_names=[ch.key for ch in v.column_headers])
        for row in v.data:
            r = []
            for e, h in zip(row, v.column_headers):
                if isinstance(e, NumericValue):
                    u = unece_unit(h.type)
                    unit = u.get('symbol')
                    r.append(Quantity(value=e.value, unit=unit))
                else:
                    r.append(_trex_value_to_python_type(e))
            table.append(r)
        return table
        


def _trex_value_to_python_type(v):
    '''Converts a TREX value to the corresponding python type'''
    if isinstance(v, NumericValue):
        if '.' not in v.value and 'E' not in v.value: 
            return int(v)
        else:
            return float(v.value)  
        
    elif isinstance(v,DateValue):
        d = v._date_time_dict
        if d.get('year') and d.get('hour'): # input is only a time
            return datetime(**d)
        elif d.get('year'):
            return date(**d)
        else:
            return time(**d)
            
    elif isinstance(v, BoolValue):
        if v.value == 'T':
            return True
        elif v.value == 'F':
            return False
        else:
            Exception(f'{v} is not valid boolean. That really should not have been possible -- Contact the maintainers of the library')
                
    elif isinstance(v, AlphanumericValue):
        return v.value
        
    elif isinstance(v, TextValue):
        decoded = from_base36(v.value)
        return decoded
        
    elif isinstance(v, BinaryValue):
        decoded = bytes(from_base36(v.value))
        return decoded
        
    elif isinstance(v, ErrorValue):
        return v.value
        
    else:
        raise (TypeError(f'Invalid type {type(v)} of segment'))
 
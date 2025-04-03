import logging
import re

from .data_model import *
from labfreed.validation import LabFREEDValidationError

class TREX_Parser():
    def __init__(self, suppress_errors=False):
        self._suppress_errors = suppress_errors
    
    def parse_trex_str(self, trex_str, name=None) -> TREX:
        trex = _from_trex_string(trex_str, name=name)
        
        trex.print_validation_messages(trex_str)
        if not trex.is_valid() and not self._suppress_errors:
            raise LabFREEDValidationError(validation_msgs = trex.get_nested_validation_messages())
        
        return trex


def _from_trex_string(trex_str, name=None, enforce_type=True) -> TREX:
    if not trex_str:
        raise ValueError(f'T-REX must be a string of non zero length')

    # remove extension indicator. Precaution in case it is not done yet
    if trex_str[0]=="*":
        trex_str=trex_str[1:-1]
    # remove line breaks. for editing T-REXes it's more convenient to have them in, so one never knows 
    trex_str = trex_str.replace('\n','')
    
    d = re.match('((?P<name>.+)\$(?P<type>.+)/)?(?P<data>.+)', trex_str).groupdict()     
    if not d:
        raise ValueError('TREX is invalid.') 
    
    type = d.get('type')
    if not type:
        logging.warning('No type given. Assume its trex')
    elif type != 'TREX' and enforce_type:
        logging.error(f'Extension type {type} is not TREX. Aborting')
        raise ValueError(f'Extension type {type} is not TREX.')
    else:
        logging.warning('Extension type {type} is not TREX. Try anyways')
        
    s_name = d.get('name')
    if name and s_name:
        logging.warning(f'conflicting names given. The string contained {s_name}, method parameter was {name}. Method parameter wins.')
    elif not name and not s_name:
        raise ValueError('No extension name was given')
    elif s_name:
        name = s_name

    data = d.get('data')
    
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
    trex._trex_str = trex_str

    return trex



def _deserialize_value_segment_from_trex_segment_str(trex_segment_str) -> ValueSegment:
    #re_scalar_pattern = re.compile(f"(?P<name>[\w\.-]*?)\$(?P<unit>[\w\.]*?):(?P<value>.*)")
    re_scalar_pattern = re.compile(f"(?P<name>.+?)\$(?P<unit>.+?):(?P<value>.+)")
    matches = re_scalar_pattern.match(trex_segment_str)
    if not matches:
        return None
    
    name, type_, value = matches.groups()
    out = ValueSegment.get_subclass(type=type_, value=value, key=name)
    return out


def _deserialize_table_segment_from_trex_segment_str(trex_segment_str) -> TREX_Table:
    # re_table_pattern = re.compile(f"(?P<tablename>[\w\.-]*?)\$\$(?P<header>[\w\.,\$:]*?)::(?P<body>.*)")
    # re_col_head_pattern = re.compile(f"(?P<name>[\w\.-]*?)\$(?P<unit>[\w\.]*)")
    re_table_pattern = re.compile(r"(?P<tablename>.+?)\$\$(?P<header>.+?)::(?P<body>.+)")
    re_col_head_pattern = re.compile(r"(?P<name>.+?)\$(?P<unit>.+)")
    
    matches = re_table_pattern.match(trex_segment_str) 
    if not matches:
        return None
    name, header, body = matches.groups()
    
    column_headers_str = header.split(':')
    
    headers = []
    for ch in column_headers_str:
         column_heads = [colhead.split('$') for colhead in ch]
         col_key = ch[0]
         col_type = ch[1] if len(ch) > 1 else ''
         headers.append(ColumnHeader(key=col_key, type=col_type))
    
    data = [row.split(':') for row in body.split('::') ]
    col_types = [h.type for h in headers]
    # convert to correct value types
    data_with_types = [[str_to_value_type(c,t) for c, t in zip(r, col_types)] for r in data]
             
    out = TREX_Table(col_headers=headers, data=data_with_types, key=name)
    return out
        

def str_to_value_type(s:str, t:str):
    match t:
        case 'T.D': v = DateValue(value=s)
        case 'T.B': v = BoolValue(value=s)
        case 'T.A': v = AlphanumericValue(value=s)
        case 'T.T': v = TextValue(value=s)
        case 'T.X': v = BinaryValue(value=s)
        case 'E'  : v = ErrorValue(value=s)
        case _    : v = NumericValue(value=s)         
    return v   
    
    



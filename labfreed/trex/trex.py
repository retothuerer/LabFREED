from collections import Counter
from datetime import date, datetime, time
import logging
import re
from typing import Self
from pydantic import Field, field_validator
from labfreed.utilities.base36 import base36, to_base36
from labfreed.python_convenience.utility_types import DataTable, Quantity, unece_unit_code_from_quantity
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, LabFREED_ValidationError
from labfreed.pac_id.extension import Extension
from labfreed.trex.table_segment import ColumnHeader, TableSegment, _deserialize_table_segment_from_trex_segment_str
from labfreed.trex.trex_base_models import AlphanumericValue, BoolValue, DateValue, NumericValue, TREX_Segment, TextValue
from labfreed.trex.value_segments import AlphanumericSegment, BoolSegment, DateSegment, NumericSegment, TextSegment, _deserialize_value_segment_from_trex_segment_str


class TREX(Extension, LabFREED_BaseModel):
    '''Represents a T-REX extension'''
    name_:str
    '''@private: helper field to capture the extension name'''
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
            seg_strings.append(s.serialize())
        s_out = '+'.join(seg_strings)
        return s_out
    
    def deserialize(trex_str, name=None, enforce_type=True, suppress_validation_errors=False) -> Self:
        if not trex_str:
            raise ValueError('T-REX must be a string of non zero length')

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
            type = 'TREX'
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
        
        trex = TREX.create(name=name, data=data)
        
        if not trex.is_valid and not suppress_validation_errors:
                raise LabFREED_ValidationError(validation_msgs = trex._get_nested_validation_messages())
            
        return trex
    
       
    def get_segment(self, segment_key:str) -> TREX_Segment:
        '''Get a segment by key'''
        s = [s for s in self.segments if s.key == segment_key]
        if s:
            return s[0]
        else:
            return None
        
        
    def update(self, segments: dict[str, Quantity|datetime|time|date|bool|str|base36|DataTable] ):
        '''update the TREX with more segments. '''
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
                    
                self.segments.append(TableSegment(key=k, column_headers=headers, data=data))
        return self
                   
                
    def to_dict(self):
        '''Converts the TREX to a python dictionary. Data is represented as python types.'''
        return {s.key: s.to_python_type() for s in self.segments}
    
    
    def serialize(self):
        return self.data()
    
    
    def __str__(self):
        s = self.data.replace('+', '\n+').replace('::', '::\n ')
        return s
            
        
        
    @field_validator('segments')
    @classmethod
    def _validate_segments(cls, segments):
        segment_keys = [s.key for s in segments]
        duplicates = [item for item, count in Counter(segment_keys).items() if count > 1]
        if duplicates:
            raise ValueError(f"Duplicate segment keys: {','.join(duplicates)}")
        return segments
      
    
        
    @staticmethod
    def create(*, name, data, type='TREX'):
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
    

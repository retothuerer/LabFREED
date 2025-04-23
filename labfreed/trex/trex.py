from collections import Counter
from typing import Self
from pydantic import Field, field_validator

from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.trex.table_segment import _deserialize_table_segment_from_trex_segment_str
from labfreed.trex.trex_base_models import TREX_Segment
from labfreed.trex.value_segments import _deserialize_value_segment_from_trex_segment_str


class TREX(LabFREED_BaseModel):
    '''Represents a T-REX extension'''
    segments: list[TREX_Segment] = Field(default_factory=list)
       
    @classmethod
    def deserialize(cls, data) -> Self:
        segment_strings = data.split('+')
        segments = list()
        for s in segment_strings:
            # there are only two valid options. The segment is a scalar or a table. 
            # Constructors do the parsing anyways and raise exceptions if invalid data
            # try both options and then let it fail
            segment = _deserialize_table_segment_from_trex_segment_str(s)
            if not segment:
                segment = _deserialize_value_segment_from_trex_segment_str(s)
            if not segment:
                raise ValueError('TREX contains neither valid value segment nor table')
                
            segments.append(segment)
        trex = TREX(segments=segments)
        return trex
        
    
    def serialize(self):
        seg_strings = list()
        for s in self.segments:
            seg_strings.append(s.serialize())
        s_out = '+'.join(seg_strings)
        return s_out
    
       
    def get_segment(self, segment_key:str) -> TREX_Segment:
        '''Get a segment by key'''
        s = [s for s in self.segments if s.key == segment_key]
        if s:
            return s[0]
        else:
            return None
        
    
    def __str__(self):
        s = self.serialize().replace('+', '\n+').replace('::', '::\n ')
        return s
            
        
        
    @field_validator('segments')
    @classmethod
    def _validate_segments(cls, segments):
        segment_keys = [s.key for s in segments]
        duplicates = [item for item, count in Counter(segment_keys).items() if count > 1]
        if duplicates:
            raise ValueError(f"Duplicate segment keys: {','.join(duplicates)}")
        return segments
      
    
        

    

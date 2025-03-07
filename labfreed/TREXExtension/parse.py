import logging
import re

from .data_model import TREX, T_REX_Segment_ParseError, TREX_SimpleSegment, TREX_Table


def from_trex_string(trex_str, enforce_type=True) -> TREX:
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
    name = d.get('name')
    data = d.get('data')
    
    if not type:
        logging.warning('No type given. Assume its trex')
    elif type != 'TREX' and enforce_type:
        logging.error(f'Extension type {type} is not TREX. Aborting')
        raise ValueError(f'Extension type {type} is not TREX.')
    else:
        logging.warning('Extension type {type} is not TREX. Try anyways')
    
            
    segment_strings = data.split('+')
    out_segments = dict()
    for s in segment_strings:
        # there are only two valid options. The segment is a scalar or a table. 
        # Constructors do the parsing anyways and raise exceptions if invalid data
        # try both options and then let it fail
        try:
            segment = TREX_SimpleSegment.from_trex_segmentstring(s)
        except T_REX_Segment_ParseError:
            segment = TREX_Table.from_trex_segmentstring(s)
        out_segments[segment.segment_name] = segment
    trex = TREX(name_= name, segments=out_segments)
    trex._trex_str = trex_str
    return trex
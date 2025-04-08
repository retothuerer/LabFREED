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
    
    trex = TREX.from_spec_fields(name=name, data=data)

    return trex





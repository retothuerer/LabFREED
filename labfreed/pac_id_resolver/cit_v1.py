
from enum import Enum
import logging
import re
import traceback

from pydantic import Field, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMessage, ValidationMsgLevel
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.services import Service, ServiceGroup
from labfreed.pac_id_resolver.cit_common import ( _add_msg_to_cit_entry_model, 
                                                 _validate_service_name, 
                                                 _validate_application_intent, 
                                                 _validate_service_type,
                                                 ServiceType)



class CITEntry_v1(LabFREED_BaseModel):
    applicable_if: str = Field(..., min_length=1)
    service_name: str = Field(..., min_length=1)
    application_intent:str = Field(..., min_length=1)
    service_type:ServiceType|str
    template_url:str = Field(..., min_length=1)
    
    
    @model_validator(mode='after')
    def _validate_model(self):
        if self.applicable_if:
            conditions = self.applicable_if.split(';')
            for c in conditions:
                if '=' in c:
                    query, expected = c.split('=')
                    query = query.strip()                      
                else:
                    query = c.strip()
                    
                try:
                    # use this function to check if the pattern is valid. it returns a PatternError if not
                    _find_pattern_in_pac(query, '')
                except PatternError:
                    self._add_validation_message(
                        level=ValidationMsgLevel.ERROR,
                        source=f'Service {self.service_name}',
                        msg=f'Applicable if contains invalid pattern {query}',
                        highlight_sub=query
                    )
                except Exception:
                    pass # if no PatternError everything is fine
        return self
    
    @model_validator(mode='after')
    def _validate_service_name(self):
        msg_dict= _validate_service_name(self.service_name)
        return _add_msg_to_cit_entry_model(msg_dict, self)
    
    
    @model_validator(mode='after')
    def _validate_application_intent(self):
        msg_dict= _validate_application_intent(self.application_intent)
        return _add_msg_to_cit_entry_model(msg_dict, self)
    
    
    @model_validator(mode='after')
    def _validate_service_type(self):
        msg_dict= _validate_service_type(self.service_type)
        return _add_msg_to_cit_entry_model(msg_dict, self)
    
    
    
    


class CIT_v1(LabFREED_BaseModel):
    origin:str = ''
    entries:list[CITEntry_v1]
    
    
    @classmethod
    def from_csv(cls, csv:str, origin=''):
        lines = csv.splitlines()
        entries = list()
        errors = list()
        for line in lines:
            if not line: # empty line
                continue
            if line.strip()[0] == '#': #comment line
                continue
            if 'Service Name' in line.strip() : #header line
                continue
            
            cols = [c.strip() for c in line.split('\t')]
            if len(cols) < 5:
                logging.error(f'invalid line {line}')
                msg = ValidationMessage(
                    level=ValidationMsgLevel.ERROR,
                    source='CIT line',
                    source_id=0,
                    msg=f'Invalid line in CIT. There are {5 - len(cols)} columns missing.',
                    highlight_sub_patterns=line
                )
                errors.append(msg)
                continue
            if len(cols) > 5:
                logging.error(f'invalid line {line}')
                msg = ValidationMessage(
                    level=ValidationMsgLevel.ERROR,
                    source='CIT line',
                    source_id=0,
                    msg=f'Invalid line in CIT. There are {len(cols) -5} too many columns',
                    highlight_sub_patterns=line
                )
                errors.append(msg)
                continue
            try:
                
                entry = CITEntry_v1(
                                    service_name         = cols[0],
                                    application_intent   = cols[1],
                                    service_type         = cols[2],
                                    applicable_if        = cols[3],
                                    template_url         = cols[4]
                                    )
                entries.append(entry) 
            except ValueError:
                logging.error(f'invalid line {line}')
                msg = ValidationMessage(
                    level=ValidationMsgLevel.ERROR,
                    source='CIT line',
                    source_id=0,
                    msg='Invalid line in CIT.',
                    highlight_sub_patterns=line
                )
                errors.append(msg)

        cit = CIT_v1(origin=origin, entries=entries)
        if not cit.is_valid:
            errors.insert(0, 
                          ValidationMessage(
                                level=ValidationMsgLevel.WARNING,
                                source='CIT ',
                                source_id=0,
                                msg='Invalid lines in CIT. The lines were ignored. The rest of the CIT is still functional',
                                highlight_sub_patterns=''
                          )
            )
        cit._validation_messages.extend(errors)
        cit._csv_original = csv
        return cit
    
    def evaluate_pac_id(self, pac:PAC_ID):
        if type(pac) is not PAC_ID:
            raise ValueError('CIT v1 does only handle PAC-IDs. PAC-CAT it does not know what to do')
        cit_evaluated = ServiceGroup(origin=self.origin)   
        for e in self.entries:
            conditions = e.applicable_if.split(';')
            conditions_evaluated = list()
            for c in conditions:
                if '=' in c:
                    query, expected = c.split('=')
                    value = _find_pattern_in_pac(query.strip(), pac)
                    conditions_evaluated.append(value == expected.strip())
                else:
                    query = c.strip()
                    found = _find_pattern_in_pac(query, pac)
                    conditions_evaluated.append(found)
            is_applicable = all(conditions_evaluated)
                    
            if not is_applicable:
                continue

            url = re.sub(r"\{([^}]+)\}", lambda v: _find_pattern_in_pac(v.group(0), pac), e.template_url)
            cit_evaluated.services.append(Service(  
                                                    service_name=e.service_name,
                                                    application_intents= [ e.application_intent ],
                                                    service_type=e.service_type,
                                                    url = url
                                )
                            )            
        return cit_evaluated
    
  
    
    def __str__(self):
        if csv:=self._csv_original:
            return csv
        
        s = "# coupling information table version: 1.0\n"
        s += "Service Name\tApplication Intent\tService Type\tApplicable If\tTemplate Url\n"
        for e in self.entries:
            s += '\t'.join([e.service_name, e.application_intent, e.service_type.value, e.applicable_if, e.template_url]) + '\n'
        return s



def _find_pattern_in_pac(value, pac:PAC_ID|str):
    if not isinstance(pac, str):
        pac_url =pac.to_url()
    else:
        pac_url = pac
        
    if value == '{isu}':
        return pac.issuer
    
    elif value == '{pac}':
        return pac_url.split('*')[0]
    
    elif value == '{id}':
        m = re.match(r'^HTTPS://.+?/(.+?)(\*.*)*$', pac_url)
        return m.group(1) if m else None
    
    elif m := re.match(r'\{idSeg(\d+)\}', value):
        i = int(m.group(1)) - 1 # CIT is 1 based
        seg = pac.identifier[i] if i < len(pac.identifier) else None
        if seg:
            return f"{(seg.key + ':') if seg.key else ''}{seg.value}"
        
    elif m := re.match(r'\{idVal(\w+)\}', value):
        k = m.group(1)
        seg = [s for s in pac.identifier if s.key and s.key == k]
        if seg:
            seg = seg[0]
            return seg.value   
        else:
            return None 
        
    elif value == '{ext}':
        m = re.match(r'^.*?(\*.*)*$', pac_url)
        ext_str = m.group(1) if m else None
        return m.group(1)[1:] if ext_str else None
    
    elif m := re.match(r'\{ext(\d+)\}', value):
        i = int(m.group(1)) - 1 # CIT is 1 based
        extensions = pac_url.split('*') 
        extensions.pop(0)# first element is not extension
        return extensions[i] if i < len(extensions) else None
    else:
        raise PatternError(f'{value} is not a recognized pattern for applicable if')
    
class PatternError(ValueError):
    pass
            

        
    
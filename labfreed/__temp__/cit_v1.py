
from enum import Enum
import logging
import re

from pydantic import Field
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMessage, ValidationMsgLevel
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.services import Service, ServiceGroup

class ServiceType(Enum):
    USER_HANDOVER_GENERIC = 'userhandover-generic'
    ATTRIBUTE_SERVICE_GENERIC = 'attributes-generic'


class CITEntry_v1(LabFREED_BaseModel):
    applicable_if: str = Field(..., min_length=1)
    service_name: str = Field(..., min_length=1)
    application_intent:str = Field(..., min_length=1)
    service_type:ServiceType
    template_url:str = Field(..., min_length=1)


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
            try:
                entry = CITEntry_v1(
                                    service_name         = cols[0],
                                    application_intent   = cols[1],
                                    service_type         = ServiceType(cols[2]),
                                    applicable_if        = cols[3],
                                    template_url         = cols[4]
                                    )
            except ValueError:
                logging.error(f'invalid line {line}')
                msg = ValidationMessage(
                    level=ValidationMsgLevel.WARNING,
                    source='CIT line',
                    source_id=0,
                    msg='Invalid line in CIT. Line was ignored. Remaining CIT is functional.',
                    highlight_sub_patterns=line
                )
                errors.append(msg)

            entries.append(entry)           
        cit = CIT_v1(origin=origin, entries=entries)
        cit._validation_messages.extend(errors)
        cit._csv_original = csv
        return cit
    
    def evaluate_pac_id(self, pac):
        cit_evaluated = ServiceGroup(origin=self.origin)   
        for e in self.entries:
            conditions = e.applicable_if.split(';')
            conditions_evaluated = list()
            for c in conditions:
                if '=' in c:
                    query, expected = c.split('=')
                    value = self._find_in_pac(query.strip(), pac)
                    conditions_evaluated.append(value == expected.strip())
                else:
                    query = c.strip()
                    found = self._find_in_pac(query, pac)
                    conditions_evaluated.append(found)
            is_applicable = all(conditions_evaluated)
                    
            if not is_applicable:
                continue

            url = re.sub(r"\{([^}]+)\}", lambda v: self._find_in_pac(v.group(0), pac), e.template_url)
            cit_evaluated.services.append(Service(  
                                                    service_name=e.service_name,
                                                    application_intents= [ e.application_intent ],
                                                    service_type=e.service_type,
                                                    url = url
                                )
                            )            
        return cit_evaluated
    
    def _find_in_pac(self, value, pac:PAC_ID):
        pac_url =pac.to_url()
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
                return f"{(seg.key + ':') if seg.key else ""}{seg.value}"
            
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
            return None
                

            
        
    
    def __str__(self):
        if csv:=self._csv_original:
            return csv
        
        s = "# coupling information table version: 1.0\n"
        s += "Service Name\tApplication Intent\tService Type\tApplicable If\tTemplate Url\n"
        for e in self.entries:
            s += '\t'.join([e.service_name, e.application_intent, e.service_type.value, e.applicable_if, e.template_url]) + '\n'
        return s

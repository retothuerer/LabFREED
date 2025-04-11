

import re
from types import MappingProxyType

from labfreed.DisplayNameExtension.DisplayNameExtension import DisplayNames
from labfreed.PAC_CAT.data_model import PAC_CAT
from labfreed.PAC_ID.extensions import Extension, UnknownExtension
from labfreed.TREX.data_model import TREX


from ..PAC_ID.data_model import *

from ..validation import ValidationMessage, LabFREEDValidationError






class PACID_With_Extensions(BaseModelWithValidationMessages):
    pac_id: PACID = Field(serialization_alias='pac')
    extensions: list[Extension] = Field(default_factory=list)
    
    def __str__(self):
        out = str(self.pac_id)
        out += '*'.join(str(e) for e in self.extensions)
        return out
        
    def get_extension_of_type(self, type:str) -> list[Extension]:
        return [e for e in self.extensions if e.type == type]
    
    def get_extension(self, name:str) -> Extension|None:
        out = [e for e in self.extensions if e.name == name]
        if not out:
            return None
        return out[0]
    
    
    def serialize(self, use_short_notation_for_extensions=False, uppercase_only=False):
        extensions_str = self._serialize_extensions(self.extensions, use_short_notation_for_extensions)
        out = self.pac_id.serialize() + extensions_str
        if uppercase_only:
            out = out.upper()
        return out
        
    def to_url(self, use_short_notation_for_extensions=False, uppercase_only=False) -> str:
        return self.serialize(use_short_notation_for_extensions, uppercase_only)
    
    @classmethod
    def deserialize(cls, url, extension_interpreters ):
        parser = PAC_Parser(extension_interpreters)
        return parser.parse(url)
        
        
    

    def _serialize_extensions(self, extensions:list[Extension], use_short_notation_for_extensions):
        out = ''
        short_notation = use_short_notation_for_extensions
        for i, e in enumerate(extensions):
            
            if short_notation and i==0:
                if e.name=='N':
                    out += f'*{e.data}'
                    continue
                else: 
                    short_notation = False
            if short_notation and i==1:
                if e.name=='SUM':
                    out += f'*{e.data}'
                    continue
                else: 
                    short_notation = False
                
            out += f'*{e.name}${e.type}/{e.data}'
        return out
        







class PAC_Parser():
    
    def __init__(self, extension_interpreters:dict[str, Extension]=None):
        self.extension_interpreters = extension_interpreters or {'TREX': TREX, 'N': DisplayNames}
        
    def parse(self, pac_url:str, suppress_errors=False) -> PACID_With_Extensions:
        if '*' in pac_url:
            id_str, ext_str = pac_url.split('*', 1)
        else:
            id_str = pac_url
            ext_str = ""
            
        pac_id = self._parse_pac_id(id_str)
        extensions = self._parse_extensions(ext_str)
        
        pac_with_extension = PACID_With_Extensions(pac_id=pac_id, extensions=extensions)
        if not pac_with_extension.is_valid() and not suppress_errors:
            raise LabFREEDValidationError(validation_msgs = pac_with_extension.get_nested_validation_messages(), model=pac_with_extension)
        
        return pac_with_extension
            
            
    def _parse_pac_id(self,id_str:str) -> PACID:
        m = re.match(f'(HTTPS://)?(PAC.)?(?P<issuer>.+?\..+?)/(?P<identifier>.*)', id_str)
        d = m.groupdict()
        
        id_segments = list()
        default_keys = None
        id_segments = self._parse_id_segments(d.get('identifier'))
        
        pac = PACID(issuer= d.get('issuer'),
                     identifier=id_segments
        )
        
        # if a segment starts with '-' the pac is interpreted as category
        if any([s for s in pac.identifier if '-' in s.value]):
            pac = PAC_CAT.from_pac_id(pac)
        
        return pac
        

    
    
    def _parse_id_segments(self, identifier:str):
        if not identifier:
            return []    
        
        id_segments = list()  
        if len(identifier) > 0 and identifier[0] == '/':
            identifier = identifier[1:]
        for s in identifier.split('/'):
            tmp = s.split(':')
            
            if len(tmp) == 1:
                segment = IDSegment(value=tmp[0])
            elif len(tmp) == 2:
                segment = IDSegment(key=tmp[0], value=tmp[1])
            else:
                raise ValueError(f'invalid segment: {s}')
                
            id_segments.append(segment)
        return id_segments
    
    


    def _parse_extensions(self, extensions_str:str|None) -> list[Extension]:    
        
        extensions = list()
        
        if not extensions_str:
            return extensions
        
        defaults =  MappingProxyType(
                                {
                                    0: { 'name': 'N', 'type': 'N'},
                                    1: { 'name': 'SUM', 'type': 'TREX'}
                                }
        )
        for i, e in enumerate(extensions_str.split('*')):
            if e == '': #this will happen if first extension starts with *
                continue
            d = re.match('((?P<name>.+)\$(?P<type>.+)/)?(?P<data>.+)', e).groupdict()
            
            name = d.get('name')
            type = d.get('type') 
            data = d.get('data')
    
            if name:
                defaults = None # once a name was specified no longer assign defaults
            else:
                if defaults:
                    name = defaults.get(i).get('name')
                    type = defaults.get(i).get('type')
                else:
                    raise ValueError('extension number {i}, must have name and type')
            
            #convert to subtype if they were given
            subtype = self.extension_interpreters.get(type) or UnknownExtension
            e = subtype.from_spec_fields(name=name, type=type, data=data)
            extensions.append(e)

        return extensions
        
 
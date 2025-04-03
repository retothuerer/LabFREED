

import re
from types import MappingProxyType
from .data_model import *

from ..validation import ValidationMessage, LabFREEDValidationError


category_conventions = MappingProxyType(
                            {
                                '-MD': ['240', '21'],
                                '-MS': ['240', '10', '20', '21', '250'],
                                '-MC': ['240', '10', '20', '21', '250'],
                                '-MM': ['240', '10', '20', '21', '250']
                            }
                        )


extension_convention = MappingProxyType(
                                {
                                    0: { 'name': 'N', 'type': 'N'},
                                    1: { 'name': 'SUM', 'type': 'TREX'}
                                }
                            )



class PAC_Parser():
    
    def __init__(self, extension_interpreters:dict[str, Extension]=None):
        self.extension_interpreters = extension_interpreters or {}
        
    def parse_pac_url(self, pac_url:str) -> tuple[PACID_With_Extensions, list[ValidationMessage] ]:
        if '*' in pac_url:
            id_str, ext_str = pac_url.split('*', 1)
        else:
            id_str = pac_url
            ext_str = ""
            
        pac_id = self.parse_pac_id(id_str)
        extensions = self.parse_extensions(ext_str)
        
        pac_with_extension = PACID_With_Extensions(pac_id=pac_id, extensions=extensions)
        pac_with_extension.print_validation_messages(pac_url)
        if not pac_with_extension.is_valid():
            raise LabFREEDValidationError(validation_msgs = pac_with_extension.get_nested_validation_messages())
        
        return pac_with_extension
            
            
    def parse_id_segments(self, identifier:str):
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
    
    
    def _apply_category_defaults(self, segments_in: list[IDSegment]):
        
        segments = segments_in.copy()
        default_keys = None
        for s in segments:
            if not s.key and default_keys:
                s.key = default_keys.pop(0)
            else:
                default_keys = None
                
            # category starts: start with new defaults. 
            if s.value in category_conventions.keys():
                default_keys = category_conventions.get(s.value).copy() #copy, so the entries can be popped when used
        return segments
                
            
        
    def parse_pac_id(self,id_str:str) -> PACID:
        m = re.match(f'(HTTPS://)?(PAC.)?(?P<issuer>.+?\..+?)/(?P<identifier>.*)', id_str)
        d = m.groupdict()
        
        id_segments = list()
        default_keys = None
        id_segments = self.parse_id_segments(d.get('identifier'))
        id_segments = self._apply_category_defaults(id_segments)
        
        pac = PACID(issuer= d.get('issuer'),
                     identifier=Identifier(segments=id_segments)
        )
        return pac


    def parse_extensions(self, extensions_str:str|None) -> list[Extension]:    
        extensions = list()
        
        if not extensions_str:
            return extensions
        
        defaults = extension_convention
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
        
 

     

if __name__ == "__main__":
    pacid_str = 'HTTPS://PAC.METTORIUS.COM/-DR/AB378/-MD/B-500/1235/-MS/AB/X:88/WWW/-MS/240:11/BB*ABCFD*A$HUR:25+B$CEL:99*BLUBB$TREX/A$HUR:25+B$CEL:99'
    
    pac = PAC_Parser().parse_pac(pacid_str)
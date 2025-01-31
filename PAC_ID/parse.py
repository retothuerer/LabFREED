

import re
from .data_model import *
from .recommendations_to_imply_keys import category_conventions





class PAC_Parser():
    
    def __init__(self, extension_interpreters:dict[str, Extension]=None):
        self.extension_interpreters = extension_interpreters or {}
        
    def parse_pac(self, pac:str) -> PACID:
        try:
            id, ext = pac.split('*', 1)
        except ValueError:
            id = pac
            ext = ""
        m = re.match(f'(HTTPS://)?(PAC.)?(?P<issuer>.+?\..+?)/(?P<identifier>.*)', id)
        d = m.groupdict()
            
        issuer = d.get('issuer')
        identifier = self._parse_identifier(d.get('identifier'))
        extensions = self._parse_extensions(ext)
            
        pac = PACID(issuer=issuer,
                    identifier=identifier,
                    extensions=extensions)
        return pac
        
    def _parse_identifier(self,identifier:str) -> Identifier:
        segments = list()
        default_keys = None
        
        for s in identifier.split('/'):
            tmp = s.split(':')
            
            if len(tmp) == 1 and default_keys:
                segment = IDSegment(key= default_keys.pop(0), value=tmp[0])
            elif len(tmp) == 1:
                segment = IDSegment(value=tmp[0])
            elif len(tmp) == 2:
                segment = IDSegment(key=tmp[0], value=tmp[1])
                default_keys = None # if a key is given we must stop assigning default values
            else:
                raise ValueError(f'invalid segment: {s}')
                
            segments.append(segment)
                
            # category starts: start with new defaults. 
            if s in category_conventions.keys():
                default_keys = category_conventions.get(s).copy() #copy, so the entries can be popped when used
                
        return Identifier(segments=segments)

    def _parse_extensions(self, extensions_str:str|None) -> list[Extension]:    
        extensions = list()
        
        if not extensions_str:
            return extensions
        
        for i, e in enumerate(extensions_str.split('*')):
            d = re.match('((?P<name>.+)\$(?P<type>.+)/)*(?P<data>.+)', e).groupdict()
            
            name = d.get('name')
            type = d.get('type') 
            data = d.get('data')
            
            if name:
                extension_convention = None # once a name was specified no longer assign defaults
            else:
                if extension_convention:
                    name = extension_convention.get(i).get('type')
                    type = extension_convention.get(i).get('name')
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
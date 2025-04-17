

import re
from types import MappingProxyType


from labfreed.display_name_extension.display_name_extension import DisplayName
from labfreed.pac_cat import PAC_CAT
from labfreed.IO.pac_id_with_extensions import  PACID_With_Extensions
from labfreed.pac_id.extension import Extension, UnknownExtension
from labfreed.pac_id.pac_id import PACID, IDSegment
from labfreed.trex import TREX



from labfreed.labfreed_infrastructure import LabFREED_ValidationError


class PAC_Parser():
    
    def __init__(self, extension_interpreters:dict[str, Extension]=None, use_pac_cat=True, suppress_validation_errors=False ):
        """ Create a PAC_Parser

        Args:
            extension_interpreters (dict[str, Extension], optional): Use this to inject your Extension Interpreters. TREX and DisplayName are known and dont need to be injected
            suppress_errors (bool, optional): Prevents raising Error when PAC-ID or extensions are invalid. Defaults to False. You can suppress errors and manually check with pac_with_extension_.is_valid()
            use_pac_cat (bool, optional): Controls if PAC-ID is converted to PAC-CAT. Default is True.
        """
        self._extension_interpreters = extension_interpreters or {'TREX': TREX, 'N': DisplayName}
        self.use_pac_cat = use_pac_cat
        self.suppress_errors = suppress_validation_errors
        
        
    def parse(self, pac_url:str) -> PACID_With_Extensions:
        """Parses a PAC-ID with extensions

        Args:
            pac_url (str): pac id with optional extensions: e.g. HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/ABC*SUM$TREX/A$T.A:ABC

        Raises:
            LabFREED_ValidationError: When validation fails. Note,that with suppress_errors no such error is raises

        Returns:
            PACID_With_Extensions:
        """
        if '*' in pac_url:
            id_str, ext_str = pac_url.split('*', 1)
        else:
            id_str = pac_url
            ext_str = ""
            
        pac_id = self._parse_pac_id(id_str)
        if self.use_pac_cat:
            pac_id = self._convert_to_pac_cat(pac_id)
        extensions = self._parse_extensions(ext_str)
        
        pac_with_extension = PACID_With_Extensions(pac_id=pac_id, extensions=extensions)
        if not pac_with_extension.is_valid and not self.suppress_errors:
            raise LabFREED_ValidationError(validation_msgs = pac_with_extension._get_nested_validation_messages())
        
        return pac_with_extension
            
            
    def _parse_pac_id(self,id_str:str) -> PACID:
        # m = re.match('(HTTPS://)?(PAC.)?(?P<issuer>.+?\..+?)/(?P<identifier>.*)', id_str)
        m = re.match('(HTTPS://)?(PAC.)?(?P<issuer>.+?)/(?P<identifier>.*)', id_str)
        d = m.groupdict()
        
        id_segments = list()
        default_keys = None
        id_segments = self._parse_id_segments(d.get('identifier'))
        
        pac = PACID(issuer= d.get('issuer'),
                     identifier=id_segments
        )
        
        return pac
    
    def _convert_to_pac_cat(self, pac_id:PACID) -> PAC_CAT:
        # if a segment starts with '-' the pac is interpreted as category
        if any([s for s in pac_id.identifier if '-' in s.value]):
            pac_cat = PAC_CAT.from_pac_id(pac_id)
            return pac_cat
        

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
            subtype = self._extension_interpreters.get(type) or UnknownExtension
            e = subtype.create(name=name, type=type, data=data)
            extensions.append(e)

        return extensions
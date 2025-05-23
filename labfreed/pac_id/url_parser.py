

import logging
import re
from types import MappingProxyType

from labfreed.labfreed_infrastructure import LabFREED_ValidationError

from labfreed.pac_id.id_segment import IDSegment
from labfreed.pac_id.extension import Extension

from labfreed.pac_cat import PAC_CAT
from labfreed.well_known_extensions import default_extension_interpreters


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # only imported during type checking
    from labfreed.pac_id import PAC_ID
    from labfreed.pac_cat import PAC_CAT

class PAC_Parser():
    '''@private
    Knows how to parse a PAC-ID. 
    From a SW engineering perspective it would be best to have no dependencies from other modules to pac_id.
    However from a Python users convenience perspective it is better to have one place where a pac url can be parsed and magically the extensions are in a meaningful type (e.g. TREX in TREX aware format) and categories are known of possible.

    >> We have given priority to convenient usage and therefore chose to have dependencies from pac_id to pac_cat and well_known_extensions
   '''
      
    @classmethod
    def from_url(cls, pac_url:str, 
                 *, 
                 extension_interpreters = 'default', 
                 try_pac_cat = True,
                 suppress_validation_errors=False
                 ) -> "PAC_ID":
        """Parses a PAC-ID with extensions

        Args:
            pac_url (str): pac id with optional extensions: e.g. HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/ABC*SUM$TREX/A$T.A:ABC

        Raises:
            LabFREED_ValidationError: When validation fails. Note,that with suppress_errors no such error is raises

        Returns:
            PACID including extensions. If possible PAC-CAT is applied and extensions are cast to a known type, which knows how to inetrprete the data
        """
        if extension_interpreters == 'default':
            extension_interpreters = default_extension_interpreters
        
        if '*' in pac_url:
            id_str, ext_str = pac_url.split('*', 1)
        else:
            id_str = pac_url
            ext_str = ""
                    
        pac_id = cls._parse_pac_id(id_str)
        
        # try converting to PAC-CAT. This can fail, in which case a regular PAC-ID is returned
        if try_pac_cat:
            try:
                pac_cat = PAC_CAT.from_pac_id(pac_id)
                if pac_cat.categories:
                    pac_id = pac_cat
            except LabFREED_ValidationError:
                pass 
              
        extensions = cls._parse_extensions(ext_str)
        if extensions and extension_interpreters:
            for i, e in enumerate(extensions):
                if interpreter := extension_interpreters.get(e.type or ''):
                    extensions[i] = interpreter.from_extension(e)
        pac_id.extensions = extensions
            
        if not pac_id.is_valid and not suppress_validation_errors:
            logging.error(pac_id.print_validation_messages())
            raise LabFREED_ValidationError(validation_msgs = pac_id._get_nested_validation_messages())
        
        return pac_id
            
    @classmethod
    def _parse_pac_id(cls,id_str:str) -> "PAC_ID":
        # m = re.match('(HTTPS://)?(PAC.)?(?P<issuer>.+?\..+?)/(?P<identifier>.*)', id_str)
        m = re.match('(HTTPS://)?(PAC.)?(?P<issuer>.+?)/(?P<identifier>.*)', id_str)
        d = m.groupdict()
        
        id_segments = list()
        id_segments = cls._parse_id_segments(d.get('identifier'))
        
        from labfreed.pac_id import PAC_ID
        pac = PAC_ID(issuer= d.get('issuer'),
                     identifier=id_segments
        )
        
        return pac
    
    @classmethod
    def _parse_id_segments(cls, identifier:str):
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
    

    @classmethod
    def _parse_extensions(cls, extensions_str:str|None) -> list["Extension"]:    
        
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
            
            #convert to subtype if they were given
            e = Extension.create(name=name, type=type, data=data)
            extensions.append(e)

        return extensions
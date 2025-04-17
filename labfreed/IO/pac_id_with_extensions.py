from pydantic import Field
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.extension import Extension
from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_id.pac_id import PACID


class PACID_With_Extensions(LabFREED_BaseModel):
    '''Represents a PAC-ID including it's extensions'''
    pac_id: PACID = Field(serialization_alias='pac')
    extensions: list[Extension] = Field(default_factory=list)
    
    def __str__(self):
        out = str(self.pac_id)
        out += '*'.join(str(e) for e in self.extensions)
        return out
        
    def get_extension_of_type(self, type:str) -> list[Extension]:
        '''Get all extensions of a certain type.'''
        return [e for e in self.extensions if e.type == type]
    
    def get_extension(self, name:str) -> Extension|None:
        '''Get extension of certain name'''
        out = [e for e in self.extensions if e.name == name]
        if not out:
            return None
        return out[0]
    
    
    def serialize(self, use_short_notation=False, uppercase_only=False) -> str:
        """Serializes the PAC-ID includind extensions.

        Args:
            use_short_notation (bool, optional): Uses shortening conventions for extensions and categories..
            uppercase_only (bool, optional): Forces all uppercase letters (results in smaller QR)..

        Returns:
            str: Something like this HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/ABC*SUM$TREX/A$T.A:ABC

        """
        extensions_str = self._serialize_extensions(self.extensions, use_short_notation)
        if isinstance(self.pac_id, PAC_CAT):
            pac_str = self.pac_id.serialize(use_short_notation=use_short_notation)
        else:
            pac_str= self.pac_id.serialize()
        out = pac_str + extensions_str
        if uppercase_only:
            out = out.upper()
        return out
        

    

        
        
    

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
        





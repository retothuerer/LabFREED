from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_cat.predefined_categories import PredefinedCategory
from labfreed.pac_id.id_segment import IDSegment
from labfreed.pac_id.extension import Extension
from labfreed.pac_id import PAC_ID  


class PACID_Serializer():
    '''Represents a PAC-ID including it's extensions'''
  
    @classmethod
    def to_url(cls, pac:PAC_ID, use_short_notation:bool|None=None, uppercase_only=False) -> str:
        """Serializes the PAC-ID including extensions.

        Args:
            use_short_notation (bool|None, optional): None (default): Preserves the identifier as is. Extensions use short form
                                                      True: forces short notation for categories and extensions
                                                      False: forces long notation for categories and extensions
            uppercase_only (bool, optional): Forces all uppercase letters (results in smaller QR)..

        Returns:
            str: Something like this HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/ABC*SUM$TREX/A$T.A:ABC

        """
        identifier_str = cls._serialize_identifier(pac, use_short_notation=use_short_notation)
        
        use_short_notation_for_extensions = True if use_short_notation is None else use_short_notation 
        extensions_str = cls._serialize_extensions(pac.extensions, use_short_notation=use_short_notation_for_extensions)
        out = f"HTTPS://PAC.{pac.issuer}{identifier_str}{extensions_str}"
        
        if uppercase_only:
            out = out.upper()
        return out
    
    @classmethod
    def _serialize_identifier(cls, pac:PAC_ID|PAC_CAT, use_short_notation:None|bool=None):
        ''' Serializes the PAC-ID'''
        
        if isinstance(pac, PAC_CAT) and use_short_notation is not None:
            segments = []
            for c in pac.categories:
                segments.append(IDSegment(value=c.key))
                if isinstance(c, PredefinedCategory):
                    segments += c._get_segments(use_short_notation=use_short_notation)
                else:
                    segments += c.segments
        else:
            segments = pac.identifier
        
        identifier_str = ''
        for s in segments:
            s:IDSegment = s
            if s.key:
                identifier_str += f'/{s.key}:{s.value}'
            else:
                identifier_str += f'/{s.value}'
        return identifier_str
          

    @classmethod
    def _serialize_extensions(cls, extensions:list[Extension], use_short_notation):
        out = ''
        short_notation = use_short_notation
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
            if e.name and e.type:
                out += f'*{e.name}${e.type}/{e.data}'
            else:
                out += f'*{e.data}'
        return out
        





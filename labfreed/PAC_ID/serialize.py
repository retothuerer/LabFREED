
from .data_model import *

    
    
class PAC_Serializer():    
    def to_url(self, pac:PACID|PACID_With_Extensions, extensions:list[Extension]=None, use_short_notation_for_extensions=False) -> str:
        if isinstance(pac, PACID_With_Extensions):
            if extensions:
                raise ValueError('Extensions were given twice, as part of PACID_With_Extension and as method parameter.')
            extensions = pac.extensions
            pac = pac.pac_id
        issuer = pac.issuer
        extensions_str = self._serialize_extensions(extensions, use_short_notation_for_extensions)
        id_segments = self._serialize_id_segments(pac.identifier.segments)
        return f"HTTPS://PAC.{issuer}{id_segments}{extensions_str}".upper()
    
    
    def _serialize_id_segments(self, segments):
        out = ''
        for s in segments:
            if s.key:
                out += f'/{s.key}:{s.value}'
            else:
                out += f'/{s.value}'
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
        

   
def main():
    pass
     

if __name__ == "__main__":
    main()
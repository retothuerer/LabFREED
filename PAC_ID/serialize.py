
from .data_model import *
from PAC_ID.recommendations_to_imply_keys import *

    
    
class PAC_Serializer():
    def to_json(pac:PACID) -> str:
        return PACID.model_dump_json()
    
    def to_pacid_str(self, pac:PACID) -> str:
        issuer = pac.issuer
        id_segments = self._serialize_id_segments()
        extensions = self._serialize_extensions()
        return f"HTTPS://{issuer}{id_segments}{extensions}"
    
    def _serialize_id_segments(self):
        pass
        def to_pacid_str(self):
            if self.key:
                return f'{self.key}:{self.value}'
            else:
                return f'{self.value}'
    
    def _serialize_extensions(self, extensions:list[Extension]):
        out = ''
        for i, e in enumerate(extensions):
            if e.name == extension_convention.get(i):
                out += f'*'
            name = e.name or extension_convention.get(i)
            if 
        
        return '*' + '*'.join([e.data for e in extensions])
        

   
def main():
    pass
     

if __name__ == "__main__":
    main()
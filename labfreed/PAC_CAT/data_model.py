from abc import ABC
from pydantic import Field
from pydantic import BaseModel

from ..PAC_ID.data_model import IDSegment, Category

class CATBase(BaseModel, ABC):
    category_key:str
    additional_segments: list[IDSegment] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True # this will allow field names, as well as aliases in validation
    
    def to_identifier_category(self, use_short_notation=False):
        '''Creates a Category with the correct segments. 
           Segments are in order of the Pydantic model fields. 
           Segment keys are omitted as long as the recommendation is followed.
           Additional segments are added at the end'''
        segments = []
        can_omit_keys = use_short_notation # keeps track of whether keys can still be omitted. That is the case when the segment recommendation is followed
        for field_name, field_info in self.model_fields.items():
            if field_name in ['category_key', 'additional_segments']:
                continue
            if value := getattr(self, field_name):
                if can_omit_keys:
                    key = None
                else:
                    key = field_info.alias
                segments.append(IDSegment(key= key, value= value)  )
            else:
                can_omit_keys = False
        if self.additional_segments:     
            segments.extend(self.additional_segments)
        return Category(key=self.category_key,
                        segments=segments)
                
            


class Material_Device(CATBase):
    category_key: str =         Field(default='-MD', frozen=True)
    model_number: str =         Field(              alias='240', min_length=1)
    serial_number: str =        Field(              alias='21', min_length=1)
    
class Material_Substance(CATBase):
    category_key: str =         Field(default='-MS', frozen=True)
    product_number:str =        Field(              alias='240', min_length=1)
    batch_number:str|None =     Field(default=None, alias='10')
    container_size:str|None =   Field(default=None, alias='20')
    container_number:str|None = Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    
class Material_Consumable(CATBase):
    category_key: str = Field(default='-MC', frozen=True)
    product_number:str =        Field(              alias='240', min_length=1)
    batch_number:str|None =     Field(default=None, alias='10')
    packing_size:str|None =     Field(default=None, alias='20')
    serial_number:str|None =    Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    
class Material_Misc(Material_Consumable):
    category_key: str = Field(default='-MM', frozen=True)



class Data_Result(CATBase):
    category_key: str = Field(default='-DR', frozen=True)
    id:str =                    Field(              alias='21', min_length=1)
    
class Data_Method(CATBase):
    category_key: str = Field(default='-DM', frozen=True)
    id:str =                    Field(              alias='21', min_length=1)
    
class Data_Calibration(CATBase):
    category_key: str = Field(default='-DC', frozen=True)
    id:str =                    Field(              alias='21', min_length=1)
    
class Data_Progress(CATBase):
    category_key: str = Field(default='-DP', frozen=True)
    id:str =                    Field(              alias='21', min_length=1)
    
class Data_Static(CATBase):
    category_key: str = Field(default='-DS', frozen=True)
    id:str =                    Field(              alias='21', min_length=1)
    
    
    
    
mapping  = {
        '-MD': Material_Device,
        '-MS': Material_Substance,
        '-MC': Material_Consumable,
        '-MM': Material_Misc,
        '-DM': Data_Method,
        '-DR': Data_Result,
        '-DC': Data_Calibration,
        '-DP': Data_Progress,
        '-DS': Data_Static 
    }
    
def CAT_from_category(category:Category) -> CATBase|None:
    raise NotImplementedError()

def CAT_from_category_key(category_key) -> CATBase|None:
    return mapping.get(category_key)
    

if __name__ == "__main__":
    pass
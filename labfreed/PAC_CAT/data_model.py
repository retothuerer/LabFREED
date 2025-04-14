from __future__ import annotations  # optional in 3.11, but recommended for consistency

from abc import ABC
from typing import Self
from pydantic import Field, computed_field, model_validator

from rich import print
from rich.text import Text
from rich.table import Table

from labfreed.validation import LabFREED_BaseModel, ValidationMsgLevel

from ..PAC_ID.data_model import PACID, IDSegment


    
class PAC_CAT(PACID):
    ''' 
    Extends a PAC-ID with interpretation of the identifier as categories
    '''
    categories:list[Category] = Field(default_factory=list)
    
    @property
    def identifier(self) -> list[IDSegment]:
        out = list()
        for category in self.categories:
            out.append(IDSegment(value=category.key))
            out.extend(category.segments)
        return out
    
    def get_category(self, key):
        tmp = [c for c in self.categories if c.key == key]
        if not tmp:
            return None
        return tmp[0]
    
    
    @classmethod
    def from_pac_id(cls, pac_id:PACID):
        d = pac_id.model_dump()
        issuer = d.get('issuer')
        
        category_segments = cls._split_into_categories(pac_id.identifier)
        categories = list()
        for c in category_segments:
            categories.append(cls.cat_from_cat_segments(c))
        
        return PAC_CAT(issuer=issuer, categories=categories, identifier=pac_id.identifier)
        
            
    @classmethod
    def cat_from_cat_segments(cls, segments:list[IDSegment]):
        segments = segments.copy()
        category_key = segments[0].value 
        segments.pop(0)
        
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
        cat = mapping.get(category_key) or Category

        # implicit segment keys
        model_dict = {v.alias: None for k, v in cat.model_fields.items() if v.alias and k not in ['key','additional_segments']}
        for k, seg in zip(model_dict.keys(), segments.copy()):
            if seg.key:
                break
            model_dict[k] = seg.value
            segments.pop(0)
            
        # try to fill model keys if not already set
        for s in segments:
            if s.key in model_dict and not model_dict.get(s.key):
                model_dict[s.key] = s.value
                segments.remove(s)
            
        model_dict['additional_segments'] = segments
        model_dict['key'] = category_key
        return cat(**model_dict)
    
    @staticmethod
    def _split_into_categories(segments:list[IDSegment]):
        categories = list()
        c_segments = list()
        categories.append(c_segments)
        for s in segments:
            # new category starts with "-"
            if s.value[0] == '-':
                cat_key = s.value
                c = [s]
                categories.append(c)
            else:
                c.append(s)
                
        # first cat can be empty > remove
        categories = [c for c in categories if len(c) > 0]
                            
        return categories
    
            
    # @computed_field
    # @property
    # def categories(self) -> list[Category]:
    #     categories = list()
    #     c = Category(segments=[])
    #     categories.append(c)
    #     for s in self.identifier:
    #         s:IDSegment = s
    #         # new category starts with "-"
    #         if s.value[0] == '-':
    #             cat_key = s.value
    #             c = Category(key=cat_key, segments=[])
    #             categories.append(c)
    #         else:
    #             c.segments.append(s)
            
    #     # the first category might have no segments. remove categories without segments
    #     if not categories[0].segments:
    #         categories = categories[1:]
                
    #     return categories
    
    @model_validator(mode='after')
    def check_keys_are_unique_in_each_category(self) -> Self:
        for c in self.categories:
            keys = [s.key for s in c.segments if s.key]
            duplicate_keys = [k for k in set(keys) if keys.count(k) > 1]
            if duplicate_keys:
                for k in duplicate_keys:
                    self.add_validation_message(
                        source=f"identifier {k}",
                        level = ValidationMsgLevel.ERROR,
                        msg=f"Duplicate key {k} in category {c.key}",
                        highlight_pattern = k
                    )
            return self
        
    def print_categories(self):
        
        table = Table(title=f'Categories in {str(self)}', show_header=False)
        table.add_column('0')
        table.add_column('1')
        s = ''
        for i, c in enumerate(self.categories):
            if i == 0:
                title = Text('Main Category', style='bold')
            else:
                title = Text('Category', style='bold')
            
            table.add_row(title)
            
            for field_name, field_info in c.model_fields.items():
                if not getattr(c, field_name):
                    continue
                table.add_row(f"{field_name} ({field_info.alias or ''})",
                              f" {getattr(c, field_name)}"
                              )      
            table.add_section()        
        print(table)
        
 

        
        
    # @classmethod
    # def from_categories(cls, issuer:str, categories:list[Category]):
    #     return PAC_CAT(issuer=issuer, identifier=cls.identifier_from_categories(categories))
        
       
    # @classmethod 
    # def identifier_from_categories(cls, categories:list[Category]) :
    #     segments = list()
    #     for c in categories:
    #         if c.key:
    #             segments.append(IDSegment(value=c.key))
    #         segments.extend(c.segments)
    #     return segments
    
    

                

class Category(LabFREED_BaseModel):
    model_config = {
        "populate_by_name": True
    }
    key:str
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)   
    
    @computed_field
    @property
    def segments(self, use_short_notation=False) -> list[IDSegment]:
        segments = []
        can_omit_keys = use_short_notation # keeps track of whether keys can still be omitted. That is the case when the segment recommendation is followed
        for field_name, field_info in self.model_fields.items():
            if field_name in ['key', 'additional_segments']:
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
            
        return segments

    
    @model_validator(mode='after')
    def warn_unusual_category_key(self):
        ''' this base class is instantiated only if the key is not a known category key'''
        if type(self) is Category:
            self.add_validation_message(
                        source=f"Category {self.key}",
                        level = ValidationMsgLevel.RECOMMENDATION,
                        msg=f'Category key {self.key} is not a well known key. It is recommended to use well known keys only',
                        highlight_pattern = f"{self.key}"
            )
        return self
    
    
    def __str__(self):
        s = '\n'.join( [f'{field_name} \t ({field_info.alias or ''}): \t {getattr(self, field_name)}' for  field_name, field_info in self.model_fields.items() if getattr(self, field_name)]) 
        return s
 

    
    
    # def to_identifier_category(self, use_short_notation=False):
    #     '''Creates a Category with the correct segments. 
    #        Segments are in order of the Pydantic model fields. 
    #        Segment keys are omitted as long as the recommendation is followed.
    #        Additional segments are added at the end'''
    #     segments = []
    #     can_omit_keys = use_short_notation # keeps track of whether keys can still be omitted. That is the case when the segment recommendation is followed
    #     for field_name, field_info in self.model_fields.items():
    #         if field_name in ['category_key', 'additional_segments']:
    #             continue
    #         if value := getattr(self, field_name):
    #             if can_omit_keys:
    #                 key = None
    #             else:
    #                 key = field_info.alias
    #             segments.append(IDSegment(key= key, value= value)  )
    #         else:
    #             can_omit_keys = False
    #     if self.additional_segments:     
    #         segments.extend(self.additional_segments)
    #     return Category(key=self.key,
    #                     segments=segments)
        
        
        
# def _apply_category_defaults(self, segments_in: list[IDSegment]):
        
#         category_conventions = MappingProxyType(
#                             {
#                                 '-MD': ['240', '21'],
#                                 '-MS': ['240', '10', '20', '21', '250'],
#                                 '-MC': ['240', '10', '20', '21', '250'],
#                                 '-MM': ['240', '10', '20', '21', '250']
#                             }
#                         )
        
#         segments = segments_in.copy()
#         default_keys = None
#         for s in segments:
#             if not s.key and default_keys:
#                 s.key = default_keys.pop(0)
#             else:
#                 default_keys = None
                
#             # category starts: start with new defaults. 
#             if s.value in category_conventions.keys():
#                 default_keys = category_conventions.get(s.value).copy() #copy, so the entries can be popped when used
#         return segments
                
            


class Material_Device(Category):
    key: str =         Field(default='-MD', frozen=True)
    model_number: str|None =         Field(              alias='240')
    serial_number: str|None =        Field(              alias='21')
    
    @model_validator(mode='after')
    def validate_mandatory_fields(self):
        if not self.model_number:
            self.add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f'Category key {self.key} is missing mandatory field Model Number',
                    highlight_pattern = f"{self.key}"
            )
        if not self.serial_number:
            self.add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f'Category key {self.key} is missing mandatory field Serial Number',
                    highlight_pattern = f"{self.key}"
            )
    
class Material_Substance(Category):
    key: str =         Field(default='-MS', frozen=True)
    product_number:str|None =    Field(              alias='240')
    batch_number:str|None =     Field(default=None, alias='10')
    container_size:str|None =   Field(default=None, alias='20')
    container_number:str|None = Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    
    @model_validator(mode='after')
    def validate_mandatory_fields(self):
        if not self.product_number:
            self.add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f'Category key {self.key} is missing mandatory field Product Number',
                    highlight_pattern = f"{self.key}"
            )
    
class Material_Consumable(Category):
    key: str = Field(default='-MC', frozen=True)
    product_number:str|None =   Field(              alias='240')
    batch_number:str|None =     Field(default=None, alias='10')
    packing_size:str|None =     Field(default=None, alias='20')
    serial_number:str|None =    Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    
    @model_validator(mode='after')
    def validate_mandatory_fields(self):
        if not self.product_number:
            self.add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"Category key {self.key} is missing mandatory field 'Product Number'",
                    highlight_pattern = f"{self.key}"
            )
    
class Material_Misc(Material_Consumable):
    key: str = Field(default='-MM', frozen=True)
    



class Data_Abstract(Category, ABC):
    key: str
    id:str|None =                    Field(              alias='21')
    
    @model_validator(mode='after')
    def validate_mandatory_fields(self):
        if not self.id:
            self.add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"Category key {self.key} is missing mandatory field 'ID'",
                    highlight_pattern = f"{self.key}"
            )

class Data_Result(Data_Abstract):
    key: str = Field(default='-DR', frozen=True)
    
class Data_Method(Data_Abstract):
    key: str = Field(default='-DM', frozen=True)
    
class Data_Calibration(Data_Abstract):
    key: str = Field(default='-DC', frozen=True)
    
class Data_Progress(Data_Abstract):
    key: str = Field(default='-DP', frozen=True)
    
class Data_Static(Data_Abstract):
    key: str = Field(default='-DS', frozen=True)
    
    
    
    
# mapping  = {
#         '-MD': Material_Device,
#         '-MS': Material_Substance,
#         '-MC': Material_Consumable,
#         '-MM': Material_Misc,
#         '-DM': Data_Method,
#         '-DR': Data_Result,
#         '-DC': Data_Calibration,
#         '-DP': Data_Progress,
#         '-DS': Data_Static 
#     }
    
# def CAT_from_category(category:Category) -> Category|None:
#     raise NotImplementedError()

# def CAT_from_category_key(category_key) -> Category|None:
#     return mapping.get(category_key)
    

# if __name__ == "__main__":
#     pass
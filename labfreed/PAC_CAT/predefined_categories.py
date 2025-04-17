## Materials
from abc import ABC
from pydantic import Field, computed_field, model_validator

from labfreed.labfreed_infrastructure import ValidationMsgLevel
from labfreed.pac_cat.category_base import Category
from labfreed.pac_id.pac_id import IDSegment

class PredefinedCategory(Category, ABC):
    '''@private 
    Base for Predefined catergories
    '''
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
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
    
    model_config = {
        "populate_by_name": True 
    }
    ''' @private Pydantic tweak to allows model fields to be populated using their Python name, even if they have an alias defined. 
        The alias we need to use the GS1 code in serialization
    '''



class Material_Device(PredefinedCategory):
    '''Represents the -MD category'''
    key: str =         Field(default='-MD', frozen=True)
    model_number: str|None =         Field(              alias='240')
    serial_number: str|None =        Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.model_number:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f'Category key {self.key} is missing mandatory field Model Number',
                    highlight_pattern = f"{self.key}"
            )
        if not self.serial_number:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f'Category key {self.key} is missing mandatory field Serial Number',
                    highlight_pattern = f"{self.key}"
            )
        return self
    
class Material_Substance(PredefinedCategory):
    '''Represents the -MS category'''
    key: str =         Field(default='-MS', frozen=True)
    product_number:str|None =    Field(              alias='240')
    batch_number:str|None =     Field(default=None, alias='10')
    container_size:str|None =   Field(default=None, alias='20')
    container_number:str|None = Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.product_number:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f'Category key {self.key} is missing mandatory field Product Number',
                    highlight_pattern = f"{self.key}"
            )
        return self
    
class Material_Consumable(PredefinedCategory):
    '''Represents the -MC category'''
    key: str = Field(default='-MC', frozen=True)
    product_number:str|None =   Field(              alias='240')
    batch_number:str|None =     Field(default=None, alias='10')
    packing_size:str|None =     Field(default=None, alias='20')
    serial_number:str|None =    Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.product_number:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"Category key {self.key} is missing mandatory field 'Product Number'",
                    highlight_pattern = f"{self.key}"
            )
        return self
    
class Material_Misc(Material_Consumable):
    '''Represents the -MC category'''
    # same fields as Consumable
    key: str = Field(default='-MM', frozen=True)
    product_number:str|None =   Field(              alias='240')
    batch_number:str|None =     Field(default=None, alias='10')
    packing_size:str|None =     Field(default=None, alias='20')
    serial_number:str|None =    Field(default=None, alias='21')
    aliquot:str|None =          Field(default=None, alias='250')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    


## Data
class Data_Abstract(PredefinedCategory, ABC):
    '''@private'''
    key: str
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    @model_validator(mode='after')
    def _validate_mandatory_fields(self):
        if not self.id:
            self._add_validation_message(
                    source=f"Category {self.key}",
                    level = ValidationMsgLevel.ERROR,
                    msg=f"Category key {self.key} is missing mandatory field 'ID'",
                    highlight_pattern = f"{self.key}"
            )
        return self

class Data_Result(Data_Abstract):
    '''Represents the -DR category'''
    key: str = Field(default='-DR', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    
class Data_Method(Data_Abstract):
    '''Represents the -DM category'''
    key: str = Field(default='-DM', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    
class Data_Calibration(Data_Abstract):
    '''Represents the -DC category'''
    key: str = Field(default='-DC', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    
class Data_Progress(Data_Abstract):
    '''Represents the -DP category'''
    key: str = Field(default='-DP', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    
class Data_Static(Data_Abstract):
    '''Represents the -DS category'''
    key: str = Field(default='-DS', frozen=True)
    id:str|None =                    Field(              alias='21')
    additional_segments: list[IDSegment] = Field(default_factory=list, exclude=True)
    ''' Category segments, which are not defined in the specification'''
    
    

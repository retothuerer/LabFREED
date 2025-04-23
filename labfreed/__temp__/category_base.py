               
from typing import Any
from pydantic import PrivateAttr, computed_field, model_validator
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, ValidationMsgLevel
from labfreed.pac_id.id_segment import IDSegment


class Category(LabFREED_BaseModel):
    '''
    Represents a category. \n
    This is the base class for categories. If possible a more specific category should be used.
    '''    
    key:str
    '''The category key, e.g. "-MD"'''
    _segments: list[IDSegment] = PrivateAttr(default_factory=list)
    
        
    @computed_field
    @property
    def segments(self) -> list[IDSegment]:
        return self._segments
    
    def __init__(self, **data: Any):
        '''@private'''
        # Pop the user-provided value for computed segments
        input_segments = data.pop("segments", None)
        super().__init__(**data)
        self._segments = input_segments
    
    @model_validator(mode='after')
    def _warn_unusual_category_key(self):
        ''' this base class is instantiated only if the key is not a known category key'''
        if type(self) is Category:
            self._add_validation_message(
                        source=f"Category {self.key}",
                        level = ValidationMsgLevel.RECOMMENDATION,
                        msg=f'Category key {self.key} is not a well known key. It is recommended to use well known keys only',
                        highlight_pattern = f"{self.key}"
            )
        return self
    
    
    def __str__(self):
        s = '\n'.join( [f'{field_name} \t ({field_info.alias or ''}): \t {getattr(self, field_name)}' for  field_name, field_info in self.model_fields.items() if getattr(self, field_name)]) 
        return s 







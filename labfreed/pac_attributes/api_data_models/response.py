
from abc import ABC
from datetime import  datetime
import re
from typing import Annotated, Any,  Literal, Union, get_args
from urllib.parse import urlparse

from labfreed.utilities.ensure_utc_time import ensure_utc
from labfreed.labfreed_infrastructure import  LabFREED_BaseModel, ValidationMsgLevel, _quote_texts
from pydantic import   Field, field_validator, model_validator


class AttributeBase(LabFREED_BaseModel, ABC):
    key: str
    value: Any
    label: str = ""
        
    def __init__(self, **data):
        # Automatically inject the Literal value for `type`
        discriminator_value = self._get_discriminator_value()
        data["type"] = discriminator_value
        super().__init__(**data)       
    
    @classmethod
    def _get_discriminator_value(cls) -> str:
        """Extract the Literal value from the 'type' annotation."""
        try:
            type_annotation = cls.__annotations__["type"]
            literal_value = get_args(type_annotation)[0]
            return literal_value
        except Exception as e:
            raise TypeError(
                f"{cls.__name__} must define `type: Literal[<value>]` annotation"
            ) from e
        
    
class DateTimeAttribute(AttributeBase):
    type: Literal["datetime"] 
    value: datetime
    
    @field_validator('value', mode='before')
    def set_utc__if_naive(cls, value):
        if isinstance(value, datetime):
            return ensure_utc(value)
        else:
            return value
        
class DateTimeListAttribute(AttributeBase):
    type: Literal["datetime-list"] 
    value: list[datetime]
    
    @field_validator('value', mode='before')
    def set_utc__if_naive(cls, value):
        value_out = []
        for v in value:
            if isinstance(v, datetime):
                value_out.append(ensure_utc(v))
            else:
                return ValueError(f'{v} is of type {type(v)}. It must be datetime')
    
    
    
class BoolAttribute(AttributeBase):
    type: Literal["bool"] 
    value: bool
    
class BoolListAttribute(AttributeBase):
    type: Literal["bool-list"] 
    value: list[bool]



    
class TextAttribute(AttributeBase):
    type: Literal["text"] 
    value: str
    
    @model_validator(mode='after')
    def _validate_value(self):
        _validate_text(self, self.value)
        return self
    
class TextListAttribute(AttributeBase):
    type: Literal["text-list"] 
    value: list[str]
    
    @model_validator(mode='after')
    def _validate_value(self):
        l = [self.value] if isinstance(self.value, str) else self.value
        for v in l:
            _validate_text(self, v)
        return self
    

def _validate_text(mdl:LabFREED_BaseModel, v):
    if len(v) > 5000: 
        mdl._add_validation_message(
            source="Text Attribute",
            level=ValidationMsgLevel.WARNING,  # noqa: F821
            msg=f"Text attribute {v} exceeds 5000 characters. It is recommended to stay below",
            highlight_pattern = f'{v}'
        )
            


class ReferenceAttribute(AttributeBase):
    type: Literal["reference"]
    value: str 
    
class ReferenceListAttribute(AttributeBase):
    type: Literal["reference-list"]
    value: list[str]
    
    
        

class ResourceAttribute(AttributeBase):
    type: Literal["resource"]
    value: str 
    
    @model_validator(mode='after')
    def _validate_value(self):
        _validate_resource(self, self.value)

class ResourceListAttribute(AttributeBase):
    type: Literal["resource-list"]
    value: list[str]
    
    @model_validator(mode='after')
    def _validate_value(self):
        value_list = self.value if isinstance(self.value, list) else [self.value]
        for v in value_list:
            _validate_resource(self, v)
        return self
    
def _validate_resource(mdl:LabFREED_BaseModel, v):
    r = urlparse(v)
    if not all([r.scheme, r.netloc]):
        mdl._add_validation_message(
            source="Resource Attribute",
            level=ValidationMsgLevel.ERROR,  # noqa: F821
            msg="Must be a valid url",
            highlight_pattern = f'{v}'
        )
    pattern = re.compile(r"\.\w{1,3}$", re.IGNORECASE)
    if not bool(pattern.search(v)):
        mdl._add_validation_message(
            source="Resource Attribute",
            level=ValidationMsgLevel.WARNING,  # noqa: F821
            msg="It is RECOMMENDED resource links end with a file extension",
            highlight_pattern = f'{v}'
        )
    
        
        
class NumericValue(LabFREED_BaseModel):
    numerical_value: str
    unit: str
    
    @model_validator(mode='after')
    def _validate_value(self):
        value = self.numerical_value
        if not_allowed_chars := set(re.sub(r'[0-9\.\-\+Ee]', '', value)):
            self._add_validation_message(
                source="Numeric Attribute",
                level=ValidationMsgLevel.ERROR,  # noqa: F821
                msg=f"Characters {_quote_texts(not_allowed_chars)} are not allowed in quantity segment. Must be a number.",
                highlight_pattern = f'{value}',
                highlight_sub=not_allowed_chars
            )
        if not re.fullmatch(r'-?\d+(\.\d+)?([Ee][\+-]?\d+)?', value):
            self._add_validation_message(
                source="Numeric Attribute",
                level=ValidationMsgLevel.ERROR,
                msg=f"{value} cannot be converted to number",
                highlight_pattern = f'{value}'               
            )
        return self
    
    @model_validator(mode="after")
    def _validate_units(self):
        '''A sanity check on unit complying with UCUM. NOTE: It is not a complete validation
        - I check for blankspaces and ^, which are often used for units, but are invalid.
        - the general structure of a ucum unit is validated, but 1)parentheses are not matched 2) units are not validated 3)prefixes are not checked
        '''
        if ' ' in self.unit or '^' in self.unit:
            self._add_validation_message(
                    source="Numeric Attribute",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Unit {self.unit} is invalid. Must not contain blankspace  or '^'.",
                    highlight_pattern = self.unit
            )
        elif not re.fullmatch(r"^(((?P<unit>[\w\[\]]+?)(?P<exponent>\-?\d+)?|(?P<annotation>)\{\w+?\})(?P<operator>[\./]?)?)+", self.unit):
            self._add_validation_message(
                    source="Numeric Attribute",
                    level= ValidationMsgLevel.WARNING,
                    msg=f"Unit {self.unit} is probably invalid. Ensure it complies with UCUM specifications.",
                    highlight_pattern = self.unit
            )
        return self
    
    


class NumericAttribute(AttributeBase):
    type: Literal["numeric"] 
    value: NumericValue 
    
class NumericListAttribute(AttributeBase):
    type: Literal["numeric-list"] 
    value: list[NumericValue]
    
    
    
class ObjectAttribute(AttributeBase):
    type: Literal["object"] 
    value: dict[str, Any]
    
    
class ObjectListAttribute(AttributeBase):
    type: Literal["object-list"] 
    value: list[dict[str, Any]]
           

     
     
Attribute = Annotated[
    Union[
        ReferenceAttribute,
        DateTimeAttribute,
        BoolAttribute,
        TextAttribute,
        NumericAttribute,
        ResourceAttribute,
        ObjectAttribute,
        
        ReferenceListAttribute,
        DateTimeListAttribute,
        BoolListAttribute,
        TextListAttribute,
        NumericListAttribute,
        ResourceListAttribute,
        ObjectListAttribute
    ],
    Field(discriminator="type")
]


class AttributeGroup(LabFREED_BaseModel):
    key: str
    label: str = ""
    attributes: list[Attribute]
       


class AttributesOfPACID(LabFREED_BaseModel):
    pac_id: str
    attribute_groups: list[AttributeGroup]
    
    

class AttributeResponsePayload(LabFREED_BaseModel):
    schema_version: str = Field(default='1.0')
    language:str 
    pac_attributes: list[AttributesOfPACID]      
    
    def to_json(self):
        return self.model_dump_json(exclude_none=True)
    
    









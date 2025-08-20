
from abc import ABC
from datetime import  datetime
import re
from typing import Annotated, Any,  Literal, Union, get_args
from labfreed.utilities.ensure_utc_time import ensure_utc
from labfreed.labfreed_infrastructure import  LabFREED_BaseModel, ValidationMsgLevel, _quote_texts
from pydantic import   Field, field_validator, model_validator


class AttributeBase(LabFREED_BaseModel, ABC):
    key: str
    value: Any
    label: str = ""
    
    observed_at: datetime | None = None
    
    def __init__(self, **data):
        # Automatically inject the Literal value for `type`
        discriminator_value = self._get_discriminator_value()
        data["type"] = discriminator_value
        super().__init__(**data)       
    
    @field_validator('observed_at', mode='before')
    def set_utc_observed_at_if_naive(cls, value):
        if isinstance(value, datetime):
            return ensure_utc(value)
        else:
            return value

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
        

        
    
class ReferenceAttribute(AttributeBase):
    type: Literal["reference"]
    value: str
    
class DateTimeAttribute(AttributeBase):
    type: Literal["datetime"] 
    value: datetime
    
    @field_validator('value', mode='before')
    def set_utc__if_naive(cls, value):
        if isinstance(value, datetime):
            return ensure_utc(value)
        else:
            return value
    
class BoolAttribute(AttributeBase):
    type: Literal["bool"] 
    value: bool
    
class TextAttribute(AttributeBase):
    type: Literal["text"] 
    value: str
    
    
    
        
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
    
class ObjectAttribute(AttributeBase):
    type: Literal["object"] 
    value: dict[str, Any]
           

     
     
Attribute = Annotated[
    Union[
        ReferenceAttribute,
        DateTimeAttribute,
        BoolAttribute,
        TextAttribute,
        NumericAttribute,
        ObjectAttribute
    ],
    Field(discriminator="type")
]

VALID_FOREVER = "forever"

class AttributeGroup(LabFREED_BaseModel):
    key: str
    label: str = ""
    attributes: list[Attribute]
    
    state_of: datetime
    valid_until: datetime | Literal["forever"] | None = None
    
    @field_validator('valid_until', mode='before')
    def set_utc_valid_until_if_naive(cls, value):
        if isinstance(value, datetime):
            return ensure_utc(value)
        else:
            return value


class AttributesOfPACID(LabFREED_BaseModel):
    pac_id: str
    attribute_groups: list[AttributeGroup]
    
    

class AttributeResponsePayload(LabFREED_BaseModel):
    schema_version: str = Field(default='1.0')
    language:str 
    pac_attributes: list[AttributesOfPACID]      
    
    def to_json(self):
        return self.model_dump_json(exclude_none=True)
    
    









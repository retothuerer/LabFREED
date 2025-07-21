
from abc import ABC
from datetime import  datetime, time
import re
from typing import Annotated, Any,  Literal, Union, get_args
from labfreed.labfreed_infrastructure import LabFREED_BaseModel, LabFREED_ValidationError, ValidationMessage, ValidationMsgLevel, _quote_texts
from pydantic import  Field,  RootModel,  model_validator

from labfreed.well_known_keys.unece.unece_units import unece_unit_codes



class DateTimeValue(RootModel[str]):    
    @model_validator(mode='after')
    def _validate(self) -> 'DateTimeValue':
        _parse_date_time_str(self.root) # raises a LabFREED_ValidationError if invalid
        return self
    
def _parse_date_time_str(value) -> dict:
        pattern = (
            r"((?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}))?"
            r"(T(?P<hour>\d{2})(?P<minute>\d{2})"
            r"(?P<second>\d{2})?(\.(?P<millisecond>\d{3}))?)?"
        )
        validation_msgs = []
        if not re.fullmatch(pattern, value):
            validation_msgs.append(ValidationMessage(source_id=0,
                                                    source=f"DateTimeValue {value}",
                                                    level=ValidationMsgLevel.ERROR,
                                                    msg=(
                                                        f"{value} is not in a valid format. Valid format for date: YYYYMMDD; "
                                                        "Valid for time: THHMM, THHMMSS, THHMMSS.SSS; "
                                                        "Datetime = any combination of valid date and time"
                                                    ),
                                                    highlight_sub_patterns=[value],
                                                )
            )

        d = {k: int(v) for k, v in re.match(pattern, value).groupdict().items() if v}
        if "millisecond" in d:
            d["microsecond"] = d.pop("millisecond") * 1000

        try:
            if "year" in d:
                datetime(**d)
            else:
                time(**d)
        except ValueError:
            validation_msgs.append(ValidationMessage(source_id=0,
                                                    source=f"TREX date value {value}",
                                                    level=ValidationMsgLevel.ERROR,
                                                    msg=f"{value} is not a valid date or time.",
                                                    highlight_sub_pattern=[value],
                                                )
            )
        
        if  validation_msgs:
            raise LabFREED_ValidationError(message='Invalid DateTime', validation_msgs=validation_msgs)
        
        return d
    
        

class AttributeBase(LabFREED_BaseModel, ABC):
    key: str
    value: Any
    
    valid_until: datetime | Literal["forever"] | None = None
    observed_at: datetime | None = None
    
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
        

        
    
class ReferenceAttribute(AttributeBase):
    type: Literal["reference"]
    value: str
    
class DateTimeAttribute(AttributeBase):
    type: Literal["datetime"] 
    value: datetime
    
class BoolAttribute(AttributeBase):
    type: Literal["bool"] 
    value: bool
    
class TextAttribute(AttributeBase):
    type: Literal["text"] 
    value: str
    

class NumericAttribute(AttributeBase):
    type: Literal["numeric"] 
    value: str
    unit: str
       
    @model_validator(mode='after')
    def _validate_value(self):
        value = self.value
        if not_allowed_chars := set(re.sub(r'[0-9\.\-E]', '', value)):
            self._add_validation_message(
                source=f"Numeric Attribute {self.key}",
                level=ValidationMsgLevel.ERROR,
                msg=f"Characters {_quote_texts(not_allowed_chars)} are not allowed in quantity segment. Must be a number.",
                highlight_pattern = f'{value}',
                highlight_sub=not_allowed_chars
            )
        if not re.fullmatch(r'-?\d+(\.\d+)?(E-?\d+)?', value):
            self._add_validation_message(
                source=f"Numeric Attribute {self.key}",
                level=ValidationMsgLevel.ERROR,
                msg=f"{value} cannot be converted to number",
                highlight_pattern = f'{value}'               
            )
        return self
    
    @model_validator(mode="after")
    def _validate_units(self):
        if self.unit not in unece_unit_codes():
            self._add_validation_message(
                    source="Attribute Value",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Unit {self.unit} is invalid. Must be a UNECE unit",
                    highlight_pattern = self.unit
            )
        return self
     
     
Attribute = Annotated[
    Union[
        ReferenceAttribute,
        DateTimeAttribute,
        BoolAttribute,
        TextAttribute,
        NumericAttribute
    ],
    Field(discriminator="type")
]

class AttributeGroup(LabFREED_BaseModel):
    key: str
    attributes: list[Attribute]


class AttributesOfPACID(LabFREED_BaseModel):
    pac_url: str
    response_from: datetime
    attribute_groups: list[AttributeGroup]
    
    
    
    
class Translations(LabFREED_BaseModel):
    key: str
    translations: dict[str, str]
    
    def __init__(self, key: str, translations: dict[str, str]):
        '''allows for init with positional arguments'''
        super().__init__(key=key, translations=translations)
    
    @model_validator(mode='after')
    def validate_language_keys(self):
        for k in self.translations.keys():
            if not re.fullmatch(r'^[a-z]{2,3}(-[a-z]{2,3})?$', k.lower()):
                self._add_validation_message(
                    source= f"Language code {k}",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Language code {k} is invalid. Must be in the format 'de' or 'de-CH'",
                    highlight_pattern = k
            )
        return self
                
    



class AttributeResponsePayload(LabFREED_BaseModel):
    schema_version: int = Field(default='1.0')
    responses: list[AttributesOfPACID]
    translations: list[Translations]|None = None
      
    
    def to_json(self):
        return self.model_dump_json(exclude_none=True)
    
    









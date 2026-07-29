
from abc import ABC
from datetime import  datetime, date
import re
from typing import  Annotated, Any,  Literal, Union
from urllib.parse import urlparse

from deprecated import deprecated

from labfreed.utilities.ensure_utc_time import ensure_utc
from labfreed.labfreed_infrastructure import  LabFREED_BaseModel, ValidationMsgLevel, _quote_texts
from pydantic import   BaseModel, Field, field_validator, model_validator



class AttributeItemsElementBase(LabFREED_BaseModel, ABC):
    value: Any
    type:str
    
    @model_validator(mode="after")
    def _no_base_instances(self):
        if type(self) is AttributeItemsElementBase:
            raise TypeError("AttributeItemsElementBase must not be instantiated")
        return self


class DateTimeAttributeItemsElement(AttributeItemsElementBase):
    type: Literal["datetime"] = "datetime"
    value: date | datetime
    
    @field_validator('value', mode='after')
    def set_utc__if_naive(cls, value):
        if isinstance(value, datetime):
            return ensure_utc(value)
        else:
            return value
        
    
    
class BoolAttributeItemsElement(AttributeItemsElementBase):
    type: Literal["bool"] = "bool"
    value: bool
    


    
class TextAttributeItemsElement(AttributeItemsElementBase):
    type: Literal["text"] = "text"
    value: str
    
    @model_validator(mode='after')
    def _validate_value(self):
        _validate_text(self, self.value)
        return self
       

def _validate_text(mdl:LabFREED_BaseModel, v):
    if len(v) > 5000: 
        mdl._add_validation_message(
            source="Text Attribute",
            level=ValidationMsgLevel.WARNING,  # noqa: F821
            msg=f"Text attribute {v} exceeds 5000 characters. It is recommended to stay below",
            highlight_pattern = f'{v}'
        )
            


class ReferenceAttributeItemsElement(AttributeItemsElementBase):
    type: Literal["reference"] = "reference"
    value: str 
    
          

class ResourceAttributeItemsElement(AttributeItemsElementBase):
    type: Literal["resource"] = "resource"
    value: str 
    
    @model_validator(mode='after')
    def _validate_value(self):
        _validate_resource(self, self.value)
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
    

class NumericAttributeItemsElement(AttributeItemsElementBase):
    type: Literal["numeric"] = "numeric"
    value: str 
    _numerical_value:str
    _unit:str
    
    @model_validator(mode='after')
    def _validate_model(self):
        self._numerical_value, self._unit = self.value.split(' ', 1)
        self._validate_value()
        self._validate_unit()
        return self

    
    def _validate_value(self):
        value = self._numerical_value
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
    
    def _validate_unit(self):
        '''A sanity check on unit complying with UCUM. NOTE: It is not a complete validation
        - I check for blankspaces and ^, which are often used for units, but are invalid.
        - the general structure of a ucum unit is validated, but 1)parentheses are not matched 2) units are not validated 3)prefixes are not checked
        '''
        if ' ' in self._unit or '^' in self._unit:
            self._add_validation_message(
                    source="Numeric Attribute",
                    level= ValidationMsgLevel.ERROR,
                    msg=f"Unit {self._unit} is invalid. Must not contain blankspace  or '^'.",
                    highlight_pattern = self._unit
            )
        elif not re.fullmatch(r"^(((?P<unit>[\w\[\]]+?)(?P<exponent>\-?\d+)?|(?P<annotation>)\{\w+?\})(?P<operator>[\./]?)?)+", self._unit):
            self._add_validation_message(
                    source="Numeric Attribute",
                    level= ValidationMsgLevel.WARNING,
                    msg=f"Unit {self._unit} is probably invalid. Ensure it complies with UCUM specifications.",
                    highlight_pattern = self._unit
            )
    
    
    
class ObjectAttributeItemsElement(AttributeItemsElementBase):
    type: Literal["object"] = "object"
    value: dict[str, Any]
    
    
AttributeItemsElement = Annotated[
    Union[
        DateTimeAttributeItemsElement,
        BoolAttributeItemsElement,
        TextAttributeItemsElement,
        NumericAttributeItemsElement,
        ReferenceAttributeItemsElement,
        ResourceAttributeItemsElement,
        ObjectAttributeItemsElement
    ],
    Field(discriminator="type"),
]
    

           
class Attribute(LabFREED_BaseModel):
    key: str|None = Field(exclude=True)
    label: str = ""
    items: list[AttributeItemsElement]
    
     

class AttributeGroup(LabFREED_BaseModel):
    group_key: str
    group_label: str = ""
    attributes: dict[str, Attribute]
    
    @field_validator("attributes", mode="before")
    @classmethod
    def set_attribute_keys(cls, v):
        if not isinstance(v, dict):
            return v

        out = {}
        for k, a in v.items():
            if isinstance(a, dict):
                # raw input dict -> inject key if missing
                out[k] = {**a, "key": a.get("key") or k}
            else:
                # already an Attribute (or something pydantic can parse)
                out[k] = a
        return out
       




class AttributesOfItem(LabFREED_BaseModel):
    id: str
    attribute_groups: list[AttributeGroup]


@deprecated("Class AttributesOfPACID is deprecated. Use it's base class instead.")
class AttributesOfPACID(AttributesOfItem):

    @model_validator(mode="before")
    @classmethod
    # field pac-id was renamed to subject-id. This is for backward compatibility.
    def _rename_to_subject_id(cls, d):
        if pac_id := d.pop('pac_id', None):
            d['id'] = pac_id
        return d

    @property
    @deprecated(" field pac_id was renamed to id.")
    def pac_id(self):
        # field pac-id was renamed to subject-id. This is for backward compatibility.
        return self.id
    
    
IMPORT_URL = "https://vocab.labfreed.org/attributes/v1.jsonld"

class AttributeResponsePayload(LabFREED_BaseModel):
    schema_version: str = Field(default='1.0')
    language:str 
    data: list[AttributesOfItem]
    
    context: str = Field(alias='@context', default=IMPORT_URL)
      
    
    def to_json(self):
        return self.model_dump_json(exclude_none=True, by_alias=True)
    
    










from datetime import UTC, date, datetime, time
import json
import logging
from typing import  Literal
from enum import Enum
import warnings
from pydantic import RootModel, field_validator, model_validator

from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_attributes.api_data_models.response import (Attribute, AttributeItemsElementBase, AttributeGroup, 
                                                              BoolAttributeItemsElement, DateTimeAttributeItemsElement, NumericAttributeItemsElement,  
                                                              ObjectAttributeItemsElement, ReferenceAttributeItemsElement,  ResourceAttributeItemsElement,
                                                              TextAttributeItemsElement)
from labfreed.pac_attributes.client.client_attribute_group import ClientAttributeGroup
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.trex.pythonic.quantity import Quantity



class pyReference(RootModel[str]):

    def __str__(self):
        return str(self.root)
    
class pyResource(RootModel[str]):

    def __str__(self):
        return str(self.root)


# the allowed scalar types
AllowedValue = str | bool | datetime | pyReference | pyResource | Quantity | int | float | dict | object
# homogeneous list of those
AllowedList = list[AllowedValue]

class pyAttribute(LabFREED_BaseModel):
    key:str
    label:str = ""
    values: AllowedValue | AllowedList
    
    @property
    def value_list(self):    
        '''helper function to more conveniently iterate over value elements, even if it's scalar'''   
        return self.values if isinstance(self.values, list) else [self.values]
    
    @model_validator(mode='before')
    def value_to_values(cls, d:dict):
        value =d.pop('value', None)
        if value is not None:
            d['values'] = value
        return d
    
    @field_validator('values', mode='before')
    def handle_one_element_list(v):
        if isinstance(v, list) and len(v)==1:
            return v[0]
        else:
            return v
        
    @field_validator('key', mode='before')
    def handle_enum_key(v):
        if isinstance(v, Enum) :
            return v.value
        else:
            return v
        
    

class pyAttributes(RootModel[list[pyAttribute]]):
    def to_payload_attributes(self) -> dict[str, Attribute]:
        out = {}
        for e in self.root:
            payload_attr = self._attribute_to_attribute_payload_type(e)
            out.update({e.key: payload_attr})
        return out
    
            
    @staticmethod        
    def _attribute_to_attribute_payload_type(attribute:pyAttribute) -> AttributeItemsElementBase:
        items = []
        for value in attribute.value_list:
            
            if isinstance(value, bool):
                items.append(BoolAttributeItemsElement(value=value))
             
            elif isinstance(value, datetime | date | time):
                if not value.tzinfo:
                    warnings.warn(f'No timezone given for {value}. Assuming it is in UTC.')
                    value.replace(tzinfo=UTC)
                items.append(DateTimeAttributeItemsElement(value=value))
                
            elif isinstance(value, Quantity|int|float):
                if not isinstance(value, Quantity):
                    value = Quantity(value=value, unit='dimensionless')
                v = f"{value.value_as_str()} {value.unit}"
                items.append(NumericAttributeItemsElement(value=v))    
                
            elif isinstance(value, str):
                # capture quantities in the form of "100.0e5 g/L"
                if Quantity.can_convert_to_quantity(value):
                    q = Quantity.from_str_with_unit(value)
                    v = f"{q.value_as_str()} {q.unit}"
                    items.append(NumericAttributeItemsElement(value=v))      
                else:
                    items.append(TextAttributeItemsElement(value=value))

            elif isinstance(value, pyReference):
                items.append(ReferenceAttributeItemsElement(value=value.root))

            elif isinstance(value, pyResource):
                items.append(ResourceAttributeItemsElement(value=value.root))
                
            elif isinstance(value, PAC_ID):
                v = value.to_url(include_extensions=False)
                items.append(ReferenceAttributeItemsElement(value=v))
                
            else: #this covers the last resort case of arbitrary objects. Must be json serializable.
                try :
                    v = json.loads(json.dumps(value))
                    items.append(ObjectAttributeItemsElement(value=v))
                except TypeError as e:  # noqa: F841
                    raise ValueError(f'Invalid Type: {type(value)} cannot be converted to attribute. You may want to use ObjectAttribute, but would have to implement the conversion from your python type yourself.')
        
                    
        if not all(type(e) is type(items[0]) for e in items):
            logging.warning("Not all elements in items have the same type. This might cause unexpected behaviour in clients.")
        
        attr = Attribute(key=attribute.key,
                         label= attribute.label,
                         items=items)
        return attr
            
  
        
    @staticmethod
    def from_payload_attributes(attributes:dict[str, Attribute]) -> 'pyAttributes':
        out = list()
        for a in attributes.values():
            values = []
            for v in a.items:
                match v:
                    case ReferenceAttributeItemsElement() :
                        values.append(pyReference(v.value))
                        
                    case ResourceAttributeItemsElement() :
                        values.append(pyResource(v.value))
                        
                    case NumericAttributeItemsElement() :                                       
                        values.append(Quantity.from_str_value(value=v._numerical_value, unit=v._unit))

                    case BoolAttributeItemsElement() :
                        values.append(v.value)
                        
                    case TextAttributeItemsElement() :
                        values.append(v.value)
                        
                    case DateTimeAttributeItemsElement() :                    
                        values.append(v.value)
                    
                    case ObjectAttributeItemsElement() :
                        values.append(v.value)
   
            attr = pyAttribute(key=a.key, 
                            label=a.label,
                            values=values
            )
            out.append(attr )
        return out
            
            
        
class pyAttributeGroup(ClientAttributeGroup):
    attributes:dict[str,pyAttribute]
    
    @staticmethod
    def from_attribute_group(attribute_group:AttributeGroup):
        data = vars(attribute_group).copy()
        data["attributes"] = {a.key: a for a in pyAttributes.from_payload_attributes(attribute_group.attributes)}
        return pyAttributeGroup(**data)
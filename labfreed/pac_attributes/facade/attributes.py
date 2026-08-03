
from datetime import UTC, date, datetime, time
import json
import logging
from enum import Enum
import warnings
from deprecated import deprecated
from pydantic import RootModel, field_validator, model_validator

from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_attributes.api_data_models.response import (Spec_Attribute, AttributeItemsElementBase, Spec_AttributeGroup,
                                                              BoolAttributeItemsElement, DateTimeAttributeItemsElement, NumericAttributeItemsElement,
                                                              ObjectAttributeItemsElement, ReferenceAttributeItemsElement,  ResourceAttributeItemsElement,
                                                              TextAttributeItemsElement)
from labfreed.pac_attributes.client.client_attribute_group import ClientAttributeGroup
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.utilities.quantity import Quantity



class Reference(RootModel[str]):

    def __str__(self):
        return str(self.root)

class Resource(RootModel[str]):

    def __str__(self):
        return str(self.root)


@deprecated("Use Reference")
class pyReference(Reference):
    '''Deprecated alias for Reference - kept for backward compatibility.'''


@deprecated("Use Resource")
class pyResource(Resource):
    '''Deprecated alias for Resource - kept for backward compatibility.'''


# the allowed scalar types
AllowedValue = str | bool | datetime | Reference | Resource | Quantity | int | float | dict | object
# homogeneous list of those
AllowedList = list[AllowedValue]

class Attribute(LabFREED_BaseModel):
    key:str
    label:str = ""
    values: AllowedValue | AllowedList
    
    @property
    def value_list(self):    
        '''helper function to more conveniently iterate over value elements, even if it's scalar'''   
        return self.values if isinstance(self.values, list) else [self.values]
    
    @property
    @deprecated
    def value(self):
        return self.values
    
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


@deprecated("Use Attribute")
class pyAttribute(Attribute):
    '''Deprecated alias for Attribute - kept for backward compatibility.'''


class Attributes(RootModel[list[Attribute]]):
    def to_payload_attributes(self) -> dict[str, Spec_Attribute]:
        out = {}
        for e in self.root:
            payload_attr = self._attribute_to_attribute_payload_type(e)
            out.update({e.key: payload_attr})
        return out


    @staticmethod
    def _attribute_to_attribute_payload_type(attribute:Attribute) -> AttributeItemsElementBase:
        items = []
        for value in attribute.value_list:
            
            if isinstance(value, bool):
                items.append(BoolAttributeItemsElement(value=value))
             
            elif isinstance(value, datetime | date | time):
                if getattr(value, 'tzinfo', None) and not value.tzinfo:
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
                q = None
                if Quantity.can_convert_to_quantity(value):
                    try:
                        q = Quantity.from_str_with_unit(value)
                    except ValueError:
                        # can_convert_to_quantity only checks "number followed by a word" -
                        # the word need not be a valid UCUM unit (e.g. "5 boxes"). Fall back to
                        # plain text rather than reject the whole attribute over it.
                        q = None
                if q is not None:
                    v = f"{q.value_as_str()} {q.unit}"
                    items.append(NumericAttributeItemsElement(value=v))
                else:
                    items.append(TextAttributeItemsElement(value=value))

            elif isinstance(value, Reference):
                items.append(ReferenceAttributeItemsElement(value=value.root))

            elif isinstance(value, Resource):
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
        
        attr = Spec_Attribute(key=attribute.key,
                         label= attribute.label,
                         items=items)
        return attr


    @staticmethod
    def from_payload_attributes(attributes:dict[str, Spec_Attribute]) -> 'Attributes':
        out = list()
        for a in attributes.values():
            values = []
            for v in a.items:
                match v:
                    case ReferenceAttributeItemsElement() :
                        values.append(Reference(v.value))

                    case ResourceAttributeItemsElement() :
                        values.append(Resource(v.value))
                        
                    case NumericAttributeItemsElement() :
                        # v._unit already went through response.py's own (non-fatal, WARNING-level)
                        # UCUM check - don't turn that warning into a hard crash here by re-validating
                        # strictly on the way back into a pythonic Quantity.
                        values.append(Quantity.from_str_value(value=v._numerical_value, unit=v._unit, dont_enforce_ucum_units=True))

                    case BoolAttributeItemsElement() :
                        values.append(v.value)
                        
                    case TextAttributeItemsElement() :
                        values.append(v.value)
                        
                    case DateTimeAttributeItemsElement() :                    
                        values.append(v.value)
                    
                    case ObjectAttributeItemsElement() :
                        values.append(v.value)
   
            attr = Attribute(key=a.key,
                            label=a.label,
                            values=values
            )
            out.append(attr )
        return out


@deprecated("Use Attributes")
class pyAttributes(Attributes):
    '''Deprecated alias for Attributes - kept for backward compatibility.'''


class AttributeGroup(ClientAttributeGroup):
    attributes:dict[str,Attribute]

    @classmethod
    def from_attribute_group(cls, attribute_group:Spec_AttributeGroup):
        data = attribute_group.model_dump()
        data["attributes"] = {a.key: a for a in Attributes.from_payload_attributes(attribute_group.attributes)}
        return cls(**data)


@deprecated("Use AttributeGroup")
class pyAttributeGroup(AttributeGroup):
    '''Deprecated alias for AttributeGroup - kept for backward compatibility.'''
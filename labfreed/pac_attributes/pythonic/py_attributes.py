
from datetime import UTC, date, datetime, time
import json
from typing import  Literal
import warnings
from pydantic import RootModel, field_validator

from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_attributes.api_data_models.response import AttributeBase, AttributeGroup, BoolAttribute, BoolListAttribute, DateTimeAttribute, DateTimeListAttribute,  NumericAttribute, NumericListAttribute, NumericValue, ObjectAttribute,ObjectListAttribute, ReferenceAttribute, ReferenceListAttribute, ResourceAttribute, ResourceListAttribute, TextAttribute, TextListAttribute
from labfreed.pac_attributes.client.attribute_cache import CacheableAttributeGroup
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
    value: AllowedValue | AllowedList
    
    @property
    def value_list(self):    
        '''helper function to more conveniently iterate over value elements, even if it's scalar'''   
        return self.value if isinstance(self.value, list) else [self.value]
    
    
    @field_validator('value', mode='before')
    def handle_one_element_list(v):
        if isinstance(v, list) and len(v)==1:
            return v[0]
        else:
            return v

class pyAttributes(RootModel[list[pyAttribute]]):
    def to_payload_attributes(self) -> list[AttributeBase]:
        out = []
        for e in self.root:
            apt = self._attribute_to_attribute_payload_type(e)
            if isinstance(apt.value, list) and len(apt.value) ==1:
                apt.value = apt.value[0]
            out.append(apt)
        return out
    
            
    @staticmethod        
    def _attribute_to_attribute_payload_type(attribute:pyAttribute) -> AttributeBase:
        common_args = {
            "key": attribute.key,
            "label": attribute.label,
        }
        value_list = attribute.value_list
        first_value = value_list[0]
        if isinstance(first_value, bool):
            if len(value_list) == 1:
                return BoolAttribute(value=value_list[0], **common_args)
            else:
                return BoolListAttribute(value=value_list, **common_args)
         
            
        elif isinstance(first_value, datetime | date | time):
            for v in value_list:
                if not v.tzinfo:
                    warnings.warn(f'No timezone given for {v}. Assuming it is in UTC.')
                    v.replace(tzinfo=UTC)
            if len(value_list) == 1:
                return DateTimeAttribute(value=value_list[0], **common_args)
            else:
                return DateTimeListAttribute(value=value_list, **common_args)
            # return DateTimeAttribute(value =_date_value_from_python_type(value).value, **common_args)
            
        
        elif isinstance(first_value, Quantity|int|float):
            values = []
            for v in value_list:
                if not isinstance(v, Quantity):
                    v = Quantity(value=v, unit='dimensionless')
                values.append(NumericValue(numerical_value=v.value_as_str(), 
                                            unit = v.unit))
            if len(values) == 1:
                num_attr = NumericAttribute(value=values[0], **common_args)
            else:
                num_attr = NumericListAttribute(value=values, **common_args)
            num_attr.print_validation_messages()
            
            return num_attr
        
        elif isinstance(first_value, str):
            # capture quantities in the form of "100.0e5 g/L"
            if Quantity.from_str_with_unit(first_value):
                values = []
                for v in value_list:
                    q = Quantity.from_str_with_unit(v)
                    values.append( NumericValue(numerical_value=q.value_as_str(), unit = q.unit) )
                if len(values) == 1:
                    return NumericAttribute(value=values[0], **common_args)
                else:
                    return NumericListAttribute(value=values, **common_args)

            else:
                if len(value_list) == 1:
                    return TextAttribute(value=value_list[0], **common_args)
                else:
                    return TextListAttribute(value=value_list, **common_args)
            
        elif isinstance(first_value, pyReference):
            values = [v.root for v in value_list]
            if len(values) == 1:
                return ReferenceAttribute(value=values[0], **common_args)
            else:
                return ReferenceListAttribute(value=values, **common_args)
        
        elif isinstance(first_value, pyResource):
            values = [v.root for v in value_list]
            if len(values) == 1:
                return ResourceAttribute(value=values[0], **common_args)
            else:
                return ResourceListAttribute(value=values, **common_args)
            
        elif isinstance(first_value, PAC_ID):
            values = [v.to_url(include_extensions=False) for v in value_list]
            if len(values) == 1:
                return ReferenceAttribute(value=values[0], **common_args)
            else:
                return ReferenceListAttribute(value=values, **common_args)
        
        else: #this covers the last resort case of arbitrary objects. Must be json serializable.
            try :
                values = [json.loads(json.dumps(v)) for v in value_list]
                if len(values) == 1:
                    return ObjectAttribute(value=values[0], **common_args)
                else:
                    return ObjectListAttribute(value=values, **common_args)
            except TypeError as e:  # noqa: F841
                raise ValueError(f'Invalid Type: {type(first_value)} cannot be converted to attribute. You may want to use ObjectAttribute, but would have to implement the conversion from your python type yourself.')
        
        
        
    @staticmethod
    def from_payload_attributes(attributes:list[AttributeBase]) -> 'pyAttributes':
        out = list()
        for a in attributes:
            value_list = a.value if isinstance(a.value, list) else [a.value]
            match a:
                case ReferenceAttribute() | ReferenceListAttribute():
                    values =  [pyReference(v) for v in value_list]
                    
                case ResourceAttribute() | ResourceListAttribute():
                    values =  [pyResource(v) for v in value_list]
                    
                case NumericAttribute() | NumericListAttribute():                                       
                    values = [ Quantity.from_str_value(value=v.numerical_value, unit=v.unit) for v in value_list]

                case BoolAttribute() | BoolListAttribute():
                    values = value_list
                    
                case TextAttribute() | TextListAttribute():
                    values = value_list
                    
                case DateTimeAttribute() | DateTimeListAttribute():                    
                    values = value_list
                
                case ObjectAttribute() | ObjectListAttribute():
                    values = value_list

                       
            attr = pyAttribute(key=a.key, 
                               label=a.label,
                               value=values
            )
            out.append(attr )
        return out
            
            
        
class pyAttributeGroup(CacheableAttributeGroup):
    attributes:dict[str,pyAttribute]
    
    @staticmethod
    def from_attribute_group(attribute_group:AttributeGroup):
        data = vars(attribute_group).copy()
        data["attributes"] = {a.key: a for a in pyAttributes.from_payload_attributes(attribute_group.attributes)}
        return pyAttributeGroup(**data)
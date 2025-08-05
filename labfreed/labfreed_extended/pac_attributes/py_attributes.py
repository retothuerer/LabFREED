
from datetime import date, datetime, time
import json
from typing import  Literal
import warnings
from pydantic import RootModel

from labfreed.labfreed_infrastructure import LabFREED_BaseModel
from labfreed.pac_attributes.api_data_models.response import AttributeBase, BoolAttribute, DateTimeAttribute,  NumericAttribute, NumericValue, ObjectAttribute, ReferenceAttribute, TextAttribute
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.trex.python_convenience.quantity import Quantity


class pyReference(RootModel[str]):
    pass

    def __str__(self):
        return str(self.root)


class pyAttribute(LabFREED_BaseModel):
    key:str
    label:str = ""
    value: str|bool|datetime|pyReference|Quantity|int|float|dict|object
    valid_until: datetime | Literal["forever"] | None = None
    observed_at: datetime | None = None
    
          

class pyAttributes(RootModel[list[pyAttribute]]):
    def to_payload_attributes(self) -> list[AttributeBase]:
        return [self._attribute_to_attribute_payload_type(e) for e in self.root]
            
    @staticmethod        
    def _attribute_to_attribute_payload_type(attribute:pyAttribute) -> AttributeBase:
        common_args = {
            "key": attribute.key,
            "label": attribute.label,
            "observed_at": attribute.observed_at
        }
        value = attribute.value
        
        if isinstance(value, bool):
            return  BoolAttribute(value=value, **common_args)
            
        elif isinstance(value, datetime | date | time):
            if not value.tzinfo:
                warnings.warn(f'No timezone given for {value}. Assuming it is in UTC.')
            return DateTimeAttribute(value =value, **common_args)
            # return DateTimeAttribute(value =_date_value_from_python_type(value).value, **common_args)
            
           
        elif isinstance(attribute.value, Quantity|int|float):
            if not isinstance(attribute.value, Quantity):
                value = Quantity(value=attribute.value, unit='dimensionless')
            num_attribute = NumericAttribute(value = NumericValue(magnitude=value.value_as_str(), 
                                             unit = value.unit),
                                              **common_args)
            num_attribute.print_validation_messages()
            return num_attribute
        
        elif isinstance(value, str):
            # capture quantities in the form of "100.0e5 g/L"
            if q := Quantity.from_str_with_unit(value):
                return NumericAttribute(value = NumericValue(magnitude=q.value_as_str(), 
                                             unit = q.unit),
                                              **common_args)
            else:
                return TextAttribute(value = value, **common_args)
            
        elif isinstance(value, pyReference):
            return ReferenceAttribute(value = value.root, **common_args)
            
        elif isinstance(value, PAC_ID):
            return ReferenceAttribute(value = value.to_url(include_extensions=False), **common_args)
        
        
        
        else: #this covers the last resort case of arbitrary objects. Must be json serializable.
            try :
                value = json.loads(json.dumps(value))
                return ObjectAttribute(value=value, **common_args)
            except TypeError as e:  # noqa: F841
                raise ValueError(f'Invalid Type: {type(value)} cannot be converted to attribute. You may want to use ObjectAttribute, but would have to implement the conversion from your python type yourself.')
        
        
    @staticmethod
    def from_payload_attributes(attributes:list[AttributeBase]) -> 'pyAttributes':
        out = dict()
        for a in attributes:
            match a:
                
                case ReferenceAttribute():
                    value =  pyReference(a.value)
                    
                case NumericAttribute():                                       
                    value = Quantity.from_str_value(value=a.value.magnitude, unit=a.value.unit)

                case BoolAttribute():
                    value = a.value
                    
                case TextAttribute():
                    value = a.value
                    
                case DateTimeAttribute():                    
                    value = a.value
                
                case ObjectAttribute():
                    value = a.value

                       
            attr = pyAttribute(key=a.key, 
                               label=a.label,
                               value=value,
                               observed_at=a.observed_at
                            #    valid_until=datetime(**_parse_date_time_str(a.valid_until)),
                            #    observed_at=datetime(**_parse_date_time_str(a.value))
            )
            out.update( { a.key: attr } )
        return out
            
            
        

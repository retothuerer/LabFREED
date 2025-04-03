from functools import cache
import json
from pathlib import Path

from rich import print

from typing import Tuple
from typing_extensions import Annotated 
from pydantic import BaseModel, AfterValidator
import quantities as pq
from quantities import  units
from  .uncertainty import to_significant_digits_str
            
                
def validate_unit(unit_name:str) -> str :
    """
    Pydantic validator function for the unit.
    Checks if the unit is a valid unit.
    

    Args:
        unit (str): unit symbol, e.g. 'kg'

    Returns:
        str: the input unit. 
        
    Errors:
        raises an AssertionError if validation fails
    """
    if hasattr(pq, unit_name):
        return unit_name
    else:
        assert False


class PydanticUncertainQuantity(BaseModel):
    data:int|float
    unit_name: Annotated[str, AfterValidator(validate_unit)]
    unit_symbol: str
    uncertainty:float|None=None
    
    @property
    def for_display(self):
        return self.__str__()
    
    def as_strings(self):
        unit_symbol = self.unit_symbol
        if unit_symbol == "dimensionless":
            unit_symbol = ""
        s = ''

        val_str = to_significant_digits_str(self.data, self.uncertainty)
        return f"{val_str}", f"{unit_symbol}", f"{val_str} {unit_symbol}"
        
    
    
    def __str__(self):
        unit_symbol = self.unit_symbol
        if unit_symbol == "dimensionless":
            unit_symbol = ""
        
        s = f"{to_significant_digits_str(self.data, self.uncertainty)} {unit_symbol}" 
        return s
    
    
unit_map = [
    ('MGM', units.milligram),
    ('GRM', units.gram),
    ('KGM', units.kilogram),
    
    ('CEL', units.celsius),
    
    ('LTR', units.liter),
    ('MLT', units.milliliter),

    ('C34', units.mole),
    ('D43',units.atomic_mass_unit),
    
    ('1', units.dimensionless),
    ('C62', units.dimensionless),
    
    ('BAR',units.bar),
    ('MBR',units.millibar),
    ('KBA',units.kilobar),
    
    ('RPM', units.rpm),
    
    ('HTZ', units.hertz),
    ('KHZ', units.kilohertz),
    ('MHZ',units.megahertz),
    
    ('SEC', units.second),
    ('MIN', units.minute),
    ('HUR', units.hour),
    
    ('MTR', units.meter)
    
]      
    


        
        
if __name__ == "__main__":
    pass                
        
        

    
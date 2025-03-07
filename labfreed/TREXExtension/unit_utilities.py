from typing import Tuple
from typing_extensions import Annotated 
from pydantic import BaseModel, AfterValidator
import quantities as pq
from quantities import Quantity, UnitQuantity, units, dimensionless
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
    ('CEL', units.celsius),
    ('LTR', units.liter),
    ('MLT', units.milliliter),
    ('GRM', units.gram),
    ('KGM', units.kilogram),
    ('C34', units.mole),
    ('D43',units.atomic_mass_unit),
    ('1', units.dimensionless),
    ('C62', units.dimensionless),
    ('BAR',units.bar),
    ('MBR',units.millibar),
    ('KBA',units.kilobar),
    ('RPM', units.rpm),
    ('HUR', units.hour),
    ('HTZ', units.hertz),
    ('KHZ', units.kilohertz),
    ('MHZ',units.megahertz),
    ('SEC', units.second),
    ('MIN', units.minute),
    ('URH', units.hour)
    
]      
    
    
def quantity_from_UN_CEFACT(value:str, unit_UN_CEFACT) -> PydanticUncertainQuantity:
    """ 
    Maps units from https://unece.org/trade/documents/revision-17-annexes-i-iii
    to an object of the quantities library https://python-quantities.readthedocs.io/en/latest/index.html 
    """
    # cast to numeric type. try int first, which will fail if string has no decimals.
    # nothing to worry yet: try floast next. if that fails the input was not a str representation of a number
    try:
        value_out = int(value)
    except ValueError:
        try: 
            value_out = float(value)
        except ValueError as e:
            raise Exception(f'Input {value} is not a str representation of a number') from e
        
    d = {um[0]: um[1] for um in unit_map}
    
    unit = d.get(unit_UN_CEFACT)
    if not unit:
        raise NotImplementedError(f"lookup for unit {unit} not implemented")
    out = PydanticUncertainQuantity(data=value_out, unit_name=unit.name, unit_symbol=unit.symbol)

    return out


def quantity_to_UN_CEFACT(value:PydanticUncertainQuantity ) -> Tuple[int|float, str]:    
    d = {um[1].symbol: um[0] for um in unit_map}
    
    unit_un_cefact = d.get(value.unit_symbol)
    if not unit_un_cefact:
        raise NotImplementedError(f"lookup for unit {value.unit_symbol} not implemented")
    return value.data, unit_un_cefact
    
    
    



        
        
        
if __name__ == "__main__":
    pass
                
        
        

    
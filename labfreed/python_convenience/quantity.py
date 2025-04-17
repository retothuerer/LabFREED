from pydantic import RootModel, computed_field
from labfreed.well_known_keys.unece.unece_units import unece_units


class Quantity(RootModel[float | int]):
    ''' Represents a quantity'''
    unit: str
    significant_digits: int|None = None
    
    @property
    @computed_field
    def value(self):
        ''' for clarity returns the value'''
        return self.root
      
    def __str__(self):
        unit_symbol = self.unit
        if self.unit == "dimensionless" or not self.unit:
            unit_symbol = ""
        
        s = f"{str(self.root)} {unit_symbol}" 
        return s
    
    
def unece_unit_code_from_quantity(q:Quantity):
        by_name =   [ u['commonCode'] for u in unece_units() if u.get('name','') == q.unit] 
        by_symbol = [ u['commonCode'] for u in unece_units() if u.get('symbol','') == q.unit]
        code = list(set(by_name) | set(by_symbol))
        if len(code) != 1:
            raise ValueError(f'No UNECE unit code found for Quantity {str(q)}' ) 
        return code[0]
    
    

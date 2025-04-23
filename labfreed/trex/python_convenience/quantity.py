from pydantic import BaseModel, model_validator
from labfreed.well_known_keys.unece.unece_units import unece_units


class Quantity(BaseModel):
    ''' Represents a quantity'''
    value: float|int
    unit: str
    significant_digits: int|None = None
    
    @model_validator(mode='after')
    def significat_digits_for_int(self):
        if isinstance(self.value, int):
            self.significant_digits = 0
        return self
        
    @property
    def float(self) -> float:
        ''' for clarity returns the value'''
        return self.value
    
    def __str__(self):
        unit_symbol = self.unit
        if self.unit == "dimensionless" or not self.unit:
            unit_symbol = ""
        if self.significant_digits is not None:
            val = f"{self.value:.{self.significant_digits}f}"
        else:
            val = str(self.value)
        return f"{val} {unit_symbol}"
      
    def __repr__(self):
        return f'Quantity: {self.__repr__()}'
    
    
    
    
def unece_unit_code_from_quantity(q:Quantity):
        by_name =   [ u['commonCode'] for u in unece_units() if u.get('name','') == q.unit] 
        by_symbol = [ u['commonCode'] for u in unece_units() if u.get('symbol','') == q.unit]
        code = list(set(by_name) | set(by_symbol))
        if len(code) != 1:
            raise ValueError(f'No UNECE unit code found for Quantity {str(q)}' ) 
        return code[0]
    
    

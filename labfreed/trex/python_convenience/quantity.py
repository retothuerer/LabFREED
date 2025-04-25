from pydantic import BaseModel, model_validator
from labfreed.well_known_keys.unece.unece_units import unece_units


class Quantity(BaseModel):
    ''' Represents a quantity'''
    value: float|int
    unit: str | None 
    '''unit. Use SI symbols. Set to None of the Quantity is dimensionless'''
    log_least_significant_digit: int|None = None
    
    @model_validator(mode='before')
    @classmethod
    def decimals_to_log_significant_digits(cls, d:dict):
        if decimals:= d.pop('decimals', None):
            d['log_least_significant_digit'] = - decimals
        return d
    
    @model_validator(mode='before')
    @classmethod
    def dimensionless_unit(cls, d:dict):
        unit= d.get('unit')
        if unit and unit in ['1', '', 'dimensionless']:
            d['unit'] = None
        return d
    
    @model_validator(mode='after')
    def significat_digits_for_int(self):
        if isinstance(self.value, int):
            self.log_least_significant_digit = 0
        return self
        
    @property
    def float(self) -> float:
        ''' for clarity returns the value'''
        return self.value
    
    def __str__(self):
        unit_symbol = self.unit
        if self.unit == "dimensionless" or not self.unit:
            unit_symbol = ""
        if self.log_least_significant_digit is not None:
            val = f"{self.value:.{self.log_least_significant_digit}f}"
        else:
            val = str(self.value)
        return f"{val} {unit_symbol}"
      
    def __repr__(self):
        return f'Quantity: {self.__repr__()}'
    
    
    
    
def unece_unit_code_from_quantity(q:Quantity):
        if not q.unit:
            return 'C62' # dimensionless
        by_name =   [ u['commonCode'] for u in unece_units() if u.get('name','') == q.unit] 
        by_symbol = [ u['commonCode'] for u in unece_units() if u.get('symbol','') == q.unit]
        by_code = [ u['commonCode'] for u in unece_units() if u.get('commonCode','') == q.unit]
        code = list(set(by_name) | set(by_symbol) | set(by_code))
        if len(code) != 1:
            raise ValueError(f'No UNECE unit code found for Quantity {q}' ) 
        return code[0]
    
    

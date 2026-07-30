import re
from pydantic import BaseModel, model_validator


class Quantity(BaseModel):
    ''' Represents a quantity'''
    value: float|int
    unit: str | None
    '''UCUM unit code. For SI units this is just the SI symbol (e.g. "kg", "m"). Set to None if the Quantity is dimensionless'''
    log_least_significant_digit: int|None = None


    @model_validator(mode='before')
    @classmethod
    def transform_inputs(cls, d:dict):
        if not isinstance(d, dict):
            return d

        # decimals_to_log_significant_digits
        if decimals:= d.pop('decimals', None):
            d['log_least_significant_digit'] = - decimals

        #dimensionless_unit
        unit:str= d.get('unit')
        if unit and unit in ['1', '', 'dimensionless']:
            unit = None
            d['unit'] = unit

        #try to coerce to ucum. catch the two most likely mistakes to use blanks for multiplication and ^ for exponents.
        if unit:
            unit = unit.replace('/ ', '/').replace(' /', '/').replace(' ', '.').replace('^', '').replace('·','.')
            d['unit'] = unit

        return d


    @model_validator(mode='after')
    def significat_digits_for_int(self):
        if isinstance(self.value, int):
            self.log_least_significant_digit = 0
        return self

    @property
    def as_float(self) -> float:
        ''' for clarity returns the value'''
        return self.value

    @classmethod
    def from_str_value(cls, value:str, unit:str|None, log_least_significant_digit=None):
        '''
        Creates a quantity from a string representing a number (e.g. -12.345E-8 ).
        It does some magic to find the least significant digit. NOTE: for numbers like 11000 it is ambiguous if the
        trailing zeros are significant. They will be treated as significant. Use scientific notation to be specific (i.e. 11e3 if the zeros are not significant)
        '''
        if '.' not in value and 'E' not in value:
            num_val = int(value)
        else:
            num_val = float(value)


        if log_least_significant_digit is None:
            log_least_significant_digit = cls._find_log_significant_digits(value)

        q = Quantity(value = num_val, unit=unit, log_least_significant_digit=log_least_significant_digit)
        return q

    @classmethod
    def can_convert_to_quantity(cls, value:str):
        ''' assumes value and unit are separated by " " '''
        m = re.match(r'^\s*(?P<mantissa>-?\d+(\.\d+)?)([Ee]-?(?P<exponent>\d+))?\s+(?P<unit>\S+)\s*$', value)
        return bool(m)

    @classmethod
    def from_str_with_unit(cls, value:str):
        ''' assumes value and unit are separated by " " '''
        m = re.match(r'^\s*(?P<mantissa>-?\d+(\.\d+)?)([Ee]-?(?P<exponent>\d+))?\s+(?P<unit>\S+)\s*$', value)
        if not m:
            print(f'{value} cannot be converted to Quantity')
            return None
        try:
            parts = value.strip().split(' ', 1)
            if len(parts) == 2:
                str_value = parts[0]
                unit = parts[1]
                return cls.from_str_value(str_value, unit)
        except Exception:
            return None

    @staticmethod
    def _find_log_significant_digits(value:str):
        s = value.strip()
        m = re.match(r'^(?P<mantissa>-?\d+(\.\d+)?)([Ee]-?(?P<exponent>\d+))?$', s)
        if m:
            exponent = int( m.group('exponent') or 0 )
            mantissa = m.group('mantissa')

        if '.' not in mantissa:
            digits_after_decimal = 0
            int_part = mantissa
            m = re.match(r'-?\d+?(?P<trailing_zeros>0*)(\.\d+)?$', int_part)
            if m:
                trailing_zeros = m.group('trailing_zeros')
                possible_non_significant_digits = len(trailing_zeros) # there is no way to know if they are really insignificant.  # noqa: F841
                log_least_significant_digit =  exponent

        else:
            int_part, frac_part = mantissa.rsplit('.', 1)
            digits_after_decimal = len(frac_part)

            log_least_significant_digit = -digits_after_decimal + exponent

        return log_least_significant_digit

    def value_as_str(self):
        if self.log_least_significant_digit is not None:
            log_digit = self.log_least_significant_digit
            if log_digit <= 0:
                val = f"{self.value:.{-log_digit}f}"
            else:
                factor = 10 ** log_digit
                rounded = round(self.value / factor) * factor
                val = str(int(rounded))
        else:
            val = str(self.value)
        return val

    def __str__(self):
        unit_symbol = self.unit
        if self.unit in [ "1", "dimensionless"] or not self.unit:
            unit_symbol = ""
        unit_symbol = unit_symbol.replace('.', '·')
        val = self.value_as_str()
        return f"{val} {unit_symbol}"

    def __repr__(self):
        return f'Quantity: {self.__repr__()}'

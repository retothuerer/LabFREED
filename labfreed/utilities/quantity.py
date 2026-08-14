import re
import warnings
from pydantic import BaseModel, model_validator

from enum import StrEnum

from labfreed.well_known_keys.unece import ucum_bridge


class Quantity(BaseModel):
    ''' Represents a quantity. `unit` must be a valid UCUM unit (checked at construction time
    against `ucum_bridge.is_valid_ucum` - structure only without the optional 'units' extra,
    full symbol-level validation with it). Pass `dont_enforce_ucum_units=True` to the
    constructor to bypass this check - discouraged, since a non-UCUM unit will silently break
    T-REX's UNECE-code mapping and PAC-ID Attributes validation later on.
    '''
    value: float|int
    unit: str | None
    '''UCUM unit code. For SI units this is just the SI symbol (e.g. "kg", "m"). Set to None if the Quantity is dimensionless'''
    log_least_significant_digit: int|None = None


    @model_validator(mode='before')
    @classmethod
    def transform_inputs(cls, d:dict):
        if not isinstance(d, dict):
            return d

        dont_enforce_ucum_units = bool(d.pop('dont_enforce_ucum_units', False))

        # decimals_to_log_significant_digits
        if decimals:= d.pop('decimals', None):
            d['log_least_significant_digit'] = - decimals

        #dimensionless_unit
        unit:str= d.get('unit')
        if unit in ['1', '', 'dimensionless']:
            unit = None
            d['unit'] = unit

        #try to coerce to ucum. catch the two most likely mistakes to use blanks for multiplication and ^ for exponents.
        if unit:
            unit = unit.replace('/ ', '/').replace(' /', '/').replace(' ', '.').replace('^', '').replace('·','.')
            d['unit'] = unit

        if unit and not dont_enforce_ucum_units and not ucum_bridge.is_valid_ucum(unit):
            extra_hint = '' if ucum_bridge.HAS_UCUM_SUPPORT else " (checked syntax only - pip install labfreed[units] for a full symbol-level check)"
            raise ValueError(
                f"Unit {unit!r} is not a valid UCUM unit{extra_hint}. See https://ucum.org/ or "
                "check it with https://lhncbc.github.io/ucum-lhc/demo.html. Pass "
                "dont_enforce_ucum_units=True to bypass this check (discouraged)."
            )

        if 'unit' in d and d['unit'] is None:
            warnings.warn(
                f"Quantity(value={d.get('value')!r}, unit=None) is unitless. LabFREED has no "
                "unitless numbers as a matter of principle - this is fine if genuinely intentional "
                "(e.g. a dimensionless GS1/UNECE C62 count), but if a bare int/float was silently "
                "wrapped for convenience, prefer passing an explicit unit instead."
            )

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
    def from_str_value(cls, value:str, unit:str|None, log_least_significant_digit=None, *, dont_enforce_ucum_units=False):
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

        q = Quantity(value = num_val, unit=unit, log_least_significant_digit=log_least_significant_digit,
                     dont_enforce_ucum_units=dont_enforce_ucum_units)
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

    @property
    def unit_display(self) -> str:
        ''' Human-readable unit for display (e.g. '°C' for the UCUM code 'Cel'), via
        ucum_bridge.pretty_print_ucum. Empty string if the quantity is dimensionless, or
        if no pretty rendering is available (neither pint nor a hardcoded fallback) -
        falls back to the raw UCUM string with '.' rendered as the UCUM multiplication
        dot '·', so display never raises.
        '''
        if not self.unit or self.unit in ["1", "dimensionless"]:
            return ""
        try:
            return ucum_bridge.pretty_print_ucum(self.unit)
        except ucum_bridge.UcumSupportError:
            return self.unit.replace('.', '·')

    def __str__(self):
        val = self.value_as_str()
        unit = self.unit_display
        return f"{val} {unit}" if unit else val

    def __repr__(self):
        return f'Quantity: {self.__str__()}'



class CommonQuantityUnit(StrEnum):
    LENGTH_METER = "m"
    LENGTH_CENTIMETER = "cm"
    LENGTH_MILLIMETER = "mm"
    LENGTH_MICROMETER = "um"
    LENGTH_NANOMETER = "nm"
    LENGTH_KILOMETER = "km"
    AREA_SQUARE_METER = "m2"
    AREA_SQUARE_CENTIMETER = "cm2"
    AREA_SQUARE_MILLIMETER = "mm2"
    VOLUME_LITER = "L"
    VOLUME_MILLILITER = "mL"
    VOLUME_MICROLITER = "uL"
    VOLUME_NANOLITER = "nL"
    VOLUME_CUBIC_METER = "m3"
    VOLUME_CUBIC_CENTIMETER = "cm3"
    WEIGHT_KILOGRAM = "kg"
    WEIGHT_GRAM = "g"
    WEIGHT_MILLIGRAM = "mg"
    WEIGHT_MICROGRAM = "ug"
    WEIGHT_NANOGRAM = "ng"
    WEIGHT_TONNE = "t"
    CONCENTRATION_MOLAR = "mol/L"
    CONCENTRATION_MILLIMOLAR = "mmol/L"
    CONCENTRATION_MICROMOLAR = "umol/L"
    CONCENTRATION_GRAM_PER_LITER = "g/L"
    CONCENTRATION_MILLIGRAM_PER_LITER = "mg/L"
    CONCENTRATION_MILLIGRAM_PER_MILLILITER = "mg/mL"
    CONCENTRATION_MICROGRAM_PER_MILLILITER = "ug/mL"
    CONCENTRATION_PERCENT = "%"
    TEMPERATURE_KELVIN = "K"
    TEMPERATURE_CELSIUS = "Cel"
    TEMPERATURE_FAHRENHEIT = "[degF]"
    PRESSURE_PASCAL = "Pa"
    PRESSURE_KILOPASCAL = "kPa"
    PRESSURE_BAR = "bar"
    PRESSURE_MILLIBAR = "mbar"
    PRESSURE_ATMOSPHERE = "atm"
    PRESSURE_MMHG = "mm[Hg]"
    PRESSURE_PSI = "[psi]"
    AMOUNT_OF_SUBSTANCE_MOLE = "mol"
    AMOUNT_OF_SUBSTANCE_MILLIMOLE = "mmol"
    AMOUNT_OF_SUBSTANCE_MICROMOLE = "umol"
    AMOUNT_OF_SUBSTANCE_NANOMOLE = "nmol"


from datetime import date, datetime, time
import logging
import re
from typing import Self

from deprecated import deprecated
from pydantic import RootModel
from labfreed.well_known_keys.unece import ucum_bridge
from labfreed.well_known_keys.unece.unece_units import unece_units
from labfreed.trex.facade.data_table import DataTable
from labfreed.utilities.base36 import from_base36, base36, to_base36

from labfreed.utilities.quantity import Quantity
from labfreed.trex.facade.typed_values import Alphanumeric, Text, Numeric, Bool, Date
from labfreed.trex.table_segment import ColumnHeader, TableSegment
from labfreed.trex.trex import Spec_T_REX
from labfreed.trex.trex_base_models import AlphanumericValue, BinaryValue, BoolValue, DateValue, ErrorValue, NumericValue, TextValue
from labfreed.trex.value_segments import BoolSegment, ErrorSegment, TextSegment, NumericSegment, AlphanumericSegment, DateSegment, ValueSegment


class T_REX(RootModel[dict[str, Quantity | int | float | datetime | time | date | bool | str | base36 | DataTable | Alphanumeric | Text | Numeric | Bool | Date | None]]):
    ''' A wrapper around dict, which knows how to convert to and from Spec_T_REX.
        It restricts the types allowed as values. Keys must be str.
    '''
    model_config = {'arbitrary_types_allowed':True} # needed to allow Quantity and DataTable w/o implementing the pydantic schema
    '''@private'''


    @classmethod
    def from_trex_spec(cls, trex:Spec_T_REX) -> Self:
        '''Creates a T_REX from a Spec_T_REX'''
        return cls({seg.key: _trex_segment_to_python_type(seg) for seg in trex.segments})


    @classmethod
    @deprecated("Use .from_trex_spec() or, for most callers, .deserialize(). Deprecated since v1.0, will be removed in v2.0.")
    def from_trex(cls, trex:Spec_T_REX) -> Self:
        '''Deprecated alias for from_trex_spec - kept for backward compatibility.'''
        return cls.from_trex_spec(trex)


    @classmethod
    def deserialize(cls, s: str) -> Self:
        '''Creates a T_REX directly from a wire string - the everyday round-trip
        counterpart to .serialize(). Prefer this over .from_trex_spec(Spec_T_REX.
        deserialize(s)) unless you actually need the intermediate Spec_T_REX object.'''
        return cls.from_trex_spec(Spec_T_REX.deserialize(s))


    def serialize(self) -> str:
        '''Serializes directly to a wire string - the everyday round-trip counterpart
        to .deserialize(). Prefer this over .to_trex_spec().serialize() unless you
        actually need the intermediate Spec_T_REX object (e.g. to hand it to a
        TREX_Extension, which is typed as Spec_T_REX).'''
        return self.to_trex_spec().serialize()


    def to_trex_spec(self) -> Spec_T_REX:
        '''Creates a Spec_T_REX'''
        segments = list()
        for k, v in self.root.items():
            v, forced_type = _normalize_explicit_value(v)
            if v is None:
                value = _error_value_from_python_type(v)
                segments.append(ErrorSegment(key=k, value=value.value))
            elif isinstance(v, bool):
                value = _bool_value_from_python_type(v)
                segments.append(BoolSegment(key=k, value=value.value))
            elif isinstance(v, Quantity):
                unece_code = unece_unit_code_from_quantity(v)
                value = _numeric_value_from_python_type(v.value)
                segments.append(NumericSegment(key=k, value=value.value, type=unece_code))
            elif isinstance(v, (datetime, time, date)):
                value = _date_value_from_python_type(v)
                segments.append(DateSegment(key=k, value=value.value))
            elif isinstance(v, str):
                if (forced_type or _classify_string(v)) == 'T.A':
                    value = _alphanumeric_value_from_python_type(v)
                    segments.append(AlphanumericSegment(key=k, value=value.value))
                else:
                    v = to_base36(v)
                    value = _text_value_from_python_type(v)
                    segments.append(TextSegment(key=k, value=value.value))
            elif isinstance(v, base36):
                value = _text_value_from_python_type(v)
                segments.append(TextSegment(key=k, value=value.value))

            elif isinstance(v, DataTable):
                v:DataTable = v
                headers = list()
                for nm, rt in zip(v.col_names, v.row_template):
                    rt, rt_forced_type = _normalize_explicit_value(rt)
                    if isinstance(rt, bool): # must come first otherwise int matches the bool
                        t = 'T.B'
                    elif isinstance(rt, Quantity):
                        unece_code = unece_unit_code_from_quantity(rt)
                        t = unece_code
                    elif isinstance(rt, (datetime, time, date)):
                        t = 'T.D'
                    elif isinstance(rt, str):
                        t = rt_forced_type or _classify_string(rt)
                    elif isinstance(rt, base36):
                        t = 'T.T'

                    headers.append(ColumnHeader(key=nm, type=t))
                data = []
                for row in v.data:
                    r = []
                    for e in row:
                        e, e_forced_type = _normalize_explicit_value(e)
                        if e is None:
                            r.append(_error_value_from_python_type(e))
                        elif isinstance(e, bool): # must come first otherwise int matches the bool
                            r.append(_bool_value_from_python_type(e))
                        elif isinstance(e, Quantity):
                            r.append(_numeric_value_from_python_type(e.value))
                        elif isinstance(e, (datetime, time, date)):
                            r.append(_date_value_from_python_type(e))
                        elif isinstance(e, str):
                            if (e_forced_type or _classify_string(e)) == 'T.A':
                                r.append(_alphanumeric_value_from_python_type(e))
                            else:
                                e = to_base36(e)
                                r.append(_text_value_from_python_type(e))
                        elif isinstance(e, base36):
                            r.append(_text_value_from_python_type(e))
                    data.append(r)
                segments.append(TableSegment(key=k, column_headers=headers, data=data))
        return Spec_T_REX(segments=segments)


    @deprecated("Use .to_trex_spec() or, for most callers, .serialize(). Deprecated since v1.0, will be removed in v2.0.")
    def to_trex(self) -> Spec_T_REX:
        '''Deprecated alias for to_trex_spec - kept for backward compatibility.'''
        return self.to_trex_spec()


    # make the usual dict methods available, for convenience
    def __getitem__(self, key): return self.root[key]
    def __setitem__(self, key, value): self.root[key] = value
    def update(self, *args, **kwargs):
        return self.root.update(*args, **kwargs)
    def keys(self): return self.root.keys()
    def values(self): return self.root.values()
    def items(self): return self.root.items()
    def __contains__(self, key): return key in self.root
    def __iter__(self): return iter(self.root)
    def __len__(self): return len(self.root)


@deprecated("Use T_REX. Deprecated since v1.0, will be removed in v2.0.")
class pyTREX(T_REX):
    '''Deprecated alias for T_REX - kept for backward compatibility.'''


# Helper functions to convert python types to TREX types

def unece_unit_code_from_quantity(q:Quantity):
    if not q.unit:
        return 'C62' # dimensionless

    # fast path: no dependency needed, correct for plain SI units where UNECE's raw fields
    # happen to equal the UCUM string (kg, m, s, ...)
    by_name =   [ u['commonCode'] for u in unece_units() if u.get('name','') == q.unit]
    by_symbol = [ u['commonCode'] for u in unece_units() if u.get('symbol','') == q.unit]
    by_code = [ u['commonCode'] for u in unece_units() if u.get('commonCode','') == q.unit]
    code = list(set(by_name) | set(by_symbol) | set(by_code))
    if len(code) == 1:
        return code[0]

    # fallback: dimensional/scale matching for compound or non-identical units (mol/L,
    # kg/m3, Cel, ...) - needs the optional 'units' extra
    if ucum_bridge.HAS_UCUM_SUPPORT:
        return ucum_bridge.best_unece_code_for_ucum(q.unit)

    raise ucum_bridge.UcumSupportError(
        f'Cannot automatically resolve a UNECE unit code for Quantity {q} (unit {q.unit!r}).'
    )


def _classify_string(s: str) -> str:
    '''Decides T.A (alphanumeric) vs. T.T (text) for an auto-detected string value -
    the one genuinely ambiguous case in this dispatch. Shared by the top-level dict
    value and both DataTable column/cell paths, so it's implemented exactly once.'''
    return 'T.A' if re.fullmatch(r'[A-Z0-9\-\.]*', s) else 'T.T'


def _normalize_explicit_value(v):
    '''Unwraps an explicit-type wrapper (Alphanumeric/Text/Numeric/Bool/Date) into the
    plain value the existing isinstance dispatch below already knows how to handle,
    and wraps a bare int/float into an explicitly-unitless Quantity - LabFREED has no
    unitless numbers (see CLAUDE.md), so this is warned about via Quantity itself and
    dispatches through the same Quantity branch as an explicit Quantity would.

    Returns (value, forced_type_or_None). forced_type is only set for Alphanumeric/
    Text, where the wrapper itself decides T.A vs. T.T instead of the auto-detect
    charset check.
    '''
    if isinstance(v, Alphanumeric):
        return v.root, 'T.A'
    if isinstance(v, Text):
        return to_base36(v.root), 'T.T'
    if isinstance(v, Numeric):
        return Quantity(value=v.root, unit=None), None
    if isinstance(v, Bool):
        return v.root, None
    if isinstance(v, Date):
        return v.root, None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return Quantity(value=v, unit=None), None
    return v, None


def _numeric_value_from_python_type(v:int|float):
    return NumericValue(value = str(v))


def _date_value_from_python_type(v:date|time|datetime):    
    sd = ""
    st = ""
    if isinstance(v, date) or isinstance(v, datetime):
        sd = v.strftime('%Y%m%d')
    if isinstance(v, time) or isinstance(v, datetime):
        if v.microsecond:
            st = v.strftime("T%H%M%S.") + f"{v.microsecond // 1000:03d}"
        elif v.second:
            st = v.strftime("T%H%M%S")
        else:
            st = v.strftime("T%H%M")
                        
    return DateValue(value = sd + st)
    
    
def _bool_value_from_python_type(v:bool):
    return BoolValue(value = 'T' if v else 'F')


def _alphanumeric_value_from_python_type(v:str):
    return AlphanumericValue(value = v)


def _text_value_from_python_type(v:base36|str):
    if isinstance(v, str):
        logging.info('Got str for text value > converting to base36')
        out =  to_base36(v).root
    else:
        out =  v.root
    return TextValue(value = out)
        
        
def _binary_value_from_python_type(v:base36|str):
    if isinstance(v, str):
        out = v
    else:
        out = v.root
    return BinaryValue(value = out)
    

def _error_value_from_python_type(v:str):
    if v is None:
        v = '-'
    return ErrorValue(value = v)
    


# Helper functions to convert from TREX types to python types
def _trex_segment_to_python_type(v):
    '''Converts a TREX segment to a python value. Note the segment key must be handles outside.'''
    if isinstance(v, NumericSegment):
        if not v.value:
            return None
        unit = ucum_bridge.ucum_for_unece_code(v.type)
        return Quantity.from_str_value(v.value, unit)
    
    # value segments are derived from their respective value type
    elif isinstance(v, ValueSegment):
        return _trex_value_to_python_type(v)

    elif isinstance(v, TableSegment):
        table = DataTable(col_names=[ch.key for ch in v.column_headers])
        for row in v.data:
            r = []
            for e, h in zip(row, v.column_headers):
                if isinstance(e, NumericValue) and e.value:
                    unit = ucum_bridge.ucum_for_unece_code(h.type)
                    r.append(Quantity.from_str_value(e.value, unit))
                else:
                    r.append(_trex_value_to_python_type(e))
            table.append(r)
        return table
        


def _trex_value_to_python_type(v):
    '''Converts a TREX value to the corresponding python type'''
    if not v.value:  # empty value is valid regardless of type - means "not defined"
        return None

    if isinstance(v, NumericValue):
        if '.' not in v.value and 'E' not in v.value: 
            return int(v.value)
        else:
            return float(v.value)  
        
    elif isinstance(v,DateValue):
        d = v._date_time_dict
        if d.get('year') and d.get('hour') is not None: # input is only a time
            return datetime(**d)
        elif d.get('year'):
            return date(**d)
        else:
            return time(**d)
            
    elif isinstance(v, BoolValue):
        if v.value == 'T':
            return True
        elif v.value == 'F':
            return False
        else:
            Exception(f'{v} is not valid boolean. That really should not have been possible -- Contact the maintainers of the library')
                
    elif isinstance(v, AlphanumericValue):
        return v.value
        
    elif isinstance(v, TextValue):
        decoded = from_base36(v.value)
        return decoded
        
    elif isinstance(v, BinaryValue):
        decoded = bytes(from_base36(v.value), encoding='utf-8')
        return decoded
        
    elif isinstance(v, ErrorValue):
        return v.value
        
    else:
        raise (TypeError(f'Invalid type {type(v)} of segment'))
 
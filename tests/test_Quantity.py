import pytest

from labfreed.trex.facade.pyTREX import T_REX
from labfreed.utilities.quantity import Quantity


def _same_physical_quantity(ucum_unit_a, ucum_unit_b):
    '''Compares two UCUM unit strings for physical equality via pint - used because
    compound-unit round trips may legitimately land on a different (but physically equal)
    UNECE code than the one originally used, since UCUM has no canonical form.'''
    from ucumvert import PintUcumRegistry
    ureg = PintUcumRegistry()
    qa = ureg.Quantity(1, ureg.from_ucum(ucum_unit_a)).to_base_units()
    qb = ureg.Quantity(1, ureg.from_ucum(ucum_unit_b)).to_base_units()
    return qa.dimensionality == qb.dimensionality and abs(qa.magnitude - qb.magnitude) < 1e-9


@pytest.mark.parametrize("unit", ["kg", "m", "s", "K", "Cel"])
def test_unambiguous_unit_roundtrips_through_trex_unchanged(unit):
    # kg/m/s/K/Cel each match exactly one UNECE code, so the round trip must return the exact
    # same UCUM string, not just a physically equal one.
    original = Quantity(value=2, unit=unit)
    data = T_REX({'X': original})
    trex = data.to_trex()
    restored = T_REX.from_trex(trex)['X']
    assert restored.value == original.value
    assert restored.unit == unit


@pytest.mark.parametrize("unit", ["kg/m3", "mol/L", "mmol/L", "ug/mL"])
def test_compound_unit_roundtrips_to_a_physically_equal_ucum_unit(unit):
    # these each match more than one UNECE code (UCUM has no canonical form) - the round trip
    # is only guaranteed to preserve the physical quantity, not the exact unit string.
    original = Quantity(value=3, unit=unit)
    data = T_REX({'X': original})
    trex = data.to_trex()
    restored = T_REX.from_trex(trex)['X']
    assert restored.value == original.value
    assert _same_physical_quantity(restored.unit, unit)


def test_roundtrip_of_simple_unit_works_without_units_extra(without_ucum_support):
    # kg's UNECE code is found by the existing exact-string fast path, which needs no
    # dependency - this must keep working even with the optional extra absent.
    original = Quantity(value=5, unit='kg')
    data = T_REX({'X': original})
    trex = data.to_trex()
    restored = T_REX.from_trex(trex)['X']
    assert restored.unit == 'kg'


def test_print_significant_digits():
    v = 111.111
    tests = [(-2, '111.11'),
             (-1, '111.1'),
             (0, '111'),
             (1, '110'), 
             (2, '100')]
    for t in tests:
        q =  Quantity(value=v, unit=None, log_least_significant_digit=t[0])
        v_rounded = q.value_as_str()
        assert  v_rounded == t[1]
        
        
        
def test_find_significant_digits():
    tests = [
            ('111.11', -2),
             ('111.1', -1),
             ('111', 0),
             ('110', 0), 
             ('100', 0),
             
             ('111.11e3', 1),
             ('111.1e3', 2),
             ('111e3', 3),
             ('110e3', 3), 
             ('100e3', 3),
             ('11e4', 4), 
             ('1e5', 5)
             ]
    for t in tests:
        log_least_significant_digit = Quantity._find_log_significant_digits(t[0])
        assert log_least_significant_digit == t[1]
    
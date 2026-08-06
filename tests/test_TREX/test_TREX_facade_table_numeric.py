import pytest

from labfreed.trex import Spec_T_REX
from labfreed.trex.facade.t_rex import T_REX
from labfreed.trex.facade.data_table import DataTable
from labfreed.utilities.quantity import Quantity


# The TableSegment branch of T_REX.from_trex() used to skip the int/float string-parsing
# step the scalar NumericSegment path did, passing the raw NumericValue string straight
# into Quantity(...) - so a whole-number cell like "90" came back as a float (90.0)
# instead of an int, and no cell got a computed log_least_significant_digit (e.g. "15.5"
# has one decimal digit -> -1). Fixed by building both the scalar and table cells via
# Quantity.from_str_value(), which parses the string to int/float and computes
# log_least_significant_digit from it in one place.

def test_table_int_cell_decodes_to_int_like_scalar_segment():
    table_trex = Spec_T_REX.deserialize('TAB$$A$MIN::15')
    scalar_trex = Spec_T_REX.deserialize('X$MIN:15')

    table_cell = T_REX.from_trex(table_trex)['TAB'].data[0][0]
    scalar_value = T_REX.from_trex(scalar_trex)['X']

    assert isinstance(table_cell.value, int)
    assert table_cell.value == 15
    assert table_cell.unit == 'min'
    assert table_cell.log_least_significant_digit == 0
    assert table_cell == scalar_value


def test_table_float_cell_decodes_to_float_like_scalar_segment():
    table_trex = Spec_T_REX.deserialize('TAB$$A$MIN::15.5')
    scalar_trex = Spec_T_REX.deserialize('X$MIN:15.5')

    table_cell = T_REX.from_trex(table_trex)['TAB'].data[0][0]
    scalar_value = T_REX.from_trex(scalar_trex)['X']

    assert isinstance(table_cell.value, float)
    assert table_cell.value == 15.5
    assert table_cell.unit == 'min'
    assert table_cell.log_least_significant_digit == -1
    assert table_cell == scalar_value


def test_table_quantity_round_trip_preserves_int_value_and_unit():
    table = DataTable(col_names=['A'], data=[[Quantity(value=90, unit=None)]])
    trex = T_REX({'TAB': table}).to_trex()

    decoded = T_REX.from_trex(trex)['TAB'].data[0][0]

    assert decoded == Quantity(value=90, unit=None)

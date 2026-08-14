'''
T_REX's dict-value type (Quantity | datetime | time | date | bool | str | base36 |
DataTable) and DataTable's cell type have no bare int/float member. Pydantic's
"smart" union mode only prefers an exact-type match over a coercion when an
exact match exists - since none did here, a plain int/float silently coerced
into a `datetime` via Unix-timestamp interpretation, before to_trex()'s own
(correctly-ordered) isinstance(v, (int, float)) check ever got a chance to see
the original value. Found independently while testing the Numeric/Bool/Date
wrapper family - not something the field-notes brief reported.

Fix: add `int | float` to both unions. Verified in isolation via a bare
TypeAdapter (no T_REX code involved) that this alone makes pydantic's smart-mode
matching pick the exact type immediately, for both the coerced case and the
already-correct ones (bool, Quantity).
'''
import datetime as dt

import pytest

from labfreed.trex.facade.t_rex import T_REX
from labfreed.trex.facade.data_table import DataTable
from labfreed.utilities.quantity import Quantity


def test_bare_int_is_not_coerced_into_a_datetime():
    assert T_REX({"X": 5})["X"] == 5
    assert isinstance(T_REX({"X": 5})["X"], int)


def test_bare_float_is_not_coerced_into_a_datetime():
    assert T_REX({"X": 5.5})["X"] == 5.5
    assert isinstance(T_REX({"X": 5.5})["X"], float)


def test_bare_int_still_serializes_as_unitless_numeric():
    seg = T_REX({"X": 5}).to_trex_spec().get_segment("X")
    assert seg.type == "C62"
    assert seg.value == "5"


def test_bool_and_quantity_and_datetime_are_unaffected_by_the_fix():
    assert T_REX({"X": True})["X"] is True
    q = Quantity(value=5, unit="kg")
    assert T_REX({"X": q})["X"] == q
    d = dt.datetime(2024, 2, 22, 17, 48)
    assert T_REX({"X": d})["X"] == d


def test_data_table_cell_int_is_not_coerced_into_a_datetime():
    table = DataTable(col_names=["M"], data=[[5], [7]])
    assert table.data[0][0] == 5
    assert isinstance(table.data[0][0], int)


def test_data_table_cell_float_is_not_coerced_into_a_datetime():
    table = DataTable(col_names=["M"], data=[[5.5], [7.5]])
    assert table.data[0][0] == 5.5
    assert isinstance(table.data[0][0], float)


def test_bare_numeric_top_level_value_warns_on_serialization():
    ''' LabFREED has no unitless numbers (CLAUDE.md) - serializing a bare int/float
    silently treats it as Quantity(v, unit=None), which must warn. '''
    with pytest.warns(UserWarning):
        T_REX({"X": 5}).to_trex_spec()


def test_data_table_column_of_bare_ints_serializes_as_unitless_numeric_and_warns():
    ''' Regression test for a masked bug: before the int|float union fix, a bare-int
    column silently became a datetime (matching the datetime branch instead of hitting
    the (missing) int/float branch here). Fixing the union alone would have turned this
    into an UnboundLocalError, since the column-type-inference loop has no int/float
    branch at all - it must be added, merged into the Quantity branch like the other two
    sites. '''
    table = DataTable(col_names=["M"], data=[[5], [7]])
    with pytest.warns(UserWarning):
        seg = T_REX({"TAB": table}).to_trex_spec().get_segment("TAB")
    assert seg.column_types == ["C62"]
    assert [v.value for v in seg.column_data("M")] == ["5", "7"]


def test_data_table_column_of_bare_floats_serializes_as_unitless_numeric_and_warns():
    table = DataTable(col_names=["M"], data=[[5.5], [7.5]])
    with pytest.warns(UserWarning):
        seg = T_REX({"TAB": table}).to_trex_spec().get_segment("TAB")
    assert seg.column_types == ["C62"]
    assert [v.value for v in seg.column_data("M")] == ["5.5", "7.5"]

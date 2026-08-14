'''
TableRow's own docstring claims "indexing, iteration, append, pop, etc." are all
supported via delegation to the wrapped list - but pydantic's RootModel does not
auto-proxy indexing, so `row[0]` currently raises TypeError, and so do
TableSegment.column_data()/cell_data(), which rely on it. Found while building
fixtures for the values_for_key() table-column matching tests (see the T-REX
spec's ENV/PH/CONDUCTIVITY example) - not something the field-notes brief
reported, an independent pre-existing bug.
'''
import pytest

from labfreed.trex.trex import Spec_T_REX


def _env_ph_conductivity_trex():
    return Spec_T_REX.deserialize(
        "ENV$$PRESSURE$BAR:TEMP$KEL::1.01:293"
        "+PH$$PH$C62:TEMP$KEL::7.01:292"
        "+CONDUCTIVITY$$COND$SIE:TEMP$KEL::1.5:295"
    )


def _titration_trex():
    ''' T-REX spec's own multi-row example - each table here has one row, which
    would make "returns the full column" indistinguishable from "returns just the
    first row"; this one has five, so a bug that only returned row 0 would be
    caught. '''
    return Spec_T_REX.deserialize(
        "TIT$$VOL$MLT:PH$C62::0.0:2.44::4.0:3.72::8.0:4.33::12.0:5.61::14.0:10.98"
    )


def test_table_row_supports_indexing():
    env = _env_ph_conductivity_trex().get_segment("ENV")
    row = env.row_data(0)
    assert row[0].value == "1.01"
    assert row[1].value == "293"


def test_column_data_returns_the_full_column():
    tit = _titration_trex().get_segment("TIT")
    assert [v.value for v in tit.column_data("PH")] == ["2.44", "3.72", "4.33", "5.61", "10.98"]


def test_cell_data_returns_a_single_cell():
    env = _env_ph_conductivity_trex().get_segment("ENV")
    assert env.cell_data(0, "TEMP").value == "293"

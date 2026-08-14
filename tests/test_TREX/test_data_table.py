import pytest

from labfreed.trex.facade.data_table import DataTable


# DataTable's row-template validator only ever inspects data[0] (the `break` isn't
# nested under the `if`) - a None in the first row fails construction even if every
# other row is fully populated. This test documents that quirk, not just the happy path.
def test_construction_raises_when_first_row_has_a_none_and_no_col_names_given():
    with pytest.raises(ValueError):
        DataTable(data=[[None, 'x']])


def test_append_raises_when_row_is_not_a_list():
    table = DataTable()
    with pytest.raises(ValueError):
        table.append((1, 2))


def test_append_raises_when_row_length_does_not_match_row_template():
    table = DataTable(col_names=['A', 'B'], data=[[1, 2]])
    with pytest.raises(ValueError):
        table.append([1])


def test_append_defaults_col_names_when_none_were_given():
    table = DataTable()
    table.append([1, 2, 3])
    assert table.col_names == ['Col0', 'Col1', 'Col2']


def test_extend_appends_all_rows_matching_the_row_template():
    table = DataTable(col_names=['A', 'B'], data=[[1, 'x']])
    table.extend([[2, 'y'], [3, 'z']])
    assert table.data == [[1, 'x'], [2, 'y'], [3, 'z']]


def test_extend_raises_when_a_row_length_does_not_match_row_template():
    table = DataTable(col_names=['A', 'B'], data=[[1, 'x']])
    with pytest.raises(ValueError):
        table.extend([[2]])


def test_get_column_by_integer_index():
    table = DataTable(col_names=['A', 'B'], data=[[1, 'x'], [2, 'y']])
    assert table.get_column(0) == [1, 2]


def test_get_row_returns_the_row_at_the_given_index():
    table = DataTable(col_names=['A', 'B'], data=[[1, 'x'], [2, 'y']])
    assert table.get_row(1) == [2, 'y']


def test_get_row_as_dict_maps_col_names_to_row_values():
    table = DataTable(col_names=['A', 'B'], data=[[1, 'x']])
    assert table.get_row_as_dict(0) == {'A': 1, 'B': 'x'}


def test_get_cell_by_integer_column_index():
    table = DataTable(col_names=['A', 'B'], data=[[1, 'x'], [2, 'y']])
    assert table.get_cell(1, 0) == 2


def test_get_cell_by_column_name():
    table = DataTable(col_names=['A', 'B'], data=[[1, 'x'], [2, 'y']])
    assert table.get_cell(1, 'B') == 'y'

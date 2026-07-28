import pytest

from labfreed.trex import TREX, TableSegment


def trex_deserialization_helper(trex_str):
    trex = TREX.deserialize(trex_str)
    return trex


    
def test_trex_parse():
    trex_str = 'A$T.A:ASDFAS+B$T.B:T'
    trex = TREX.deserialize(trex_str)
    seg = trex.get_segment('A')
    assert seg.type == 'T.A'
    assert seg.value == 'ASDFAS'
    seg = trex.get_segment('B')
    assert seg.type == 'T.B'
    assert seg.value == 'T'
    
    
    
    
# Segment Key   
def test_invalid_keys():
    trex_str = '£TIM$HUR:1'
    trex = trex_deserialization_helper(trex_str)
    assert not trex.is_valid
        
    trex_str = 'tImE$HUR:1'
    trex = trex_deserialization_helper(trex_str)
    assert not trex.is_valid


# Numeric Segment
def test_numeric_segment_valid():
    valid_strs = [
        'TIME$HUR:25.0',
        'TIME$HUR:25',
        'TIME$HUR:-25.0',
        'TIME$HUR:-25'
    ]
    for trex_str in valid_strs:
        trex = trex_deserialization_helper(trex_str)
        assert trex.serialize() == trex_str
    

        
def test_numeric_segment_scientific_valid():   
    valid_strs = [
        'TIME$HUR:-25E2',
        'TIME$HUR:-25E-2',
        'TIME$HUR:-25.12E2',
        'TIME$HUR:-25.12E-2'
    ]
    for trex_str in valid_strs:
        trex = trex_deserialization_helper(trex_str)
        assert trex.serialize() == trex_str

    
    
def test_numeric_segment_invalid_values():
    trex_str ='TIME$HUR:A'
    trex = trex_deserialization_helper(trex_str)
    assert not trex.is_valid
    assert trex.serialize() == trex_str
    
    trex_str ='TIME$HUR:1.1.1'
    trex = trex_deserialization_helper(trex_str)
    assert not trex.is_valid
    assert trex.serialize() == trex_str
        
def test_numeric_segment_invalid_unit():
    trex_str ='TIME$HIP:A'
    trex = trex_deserialization_helper(trex_str)
    assert not trex.is_valid
    assert trex.serialize() == trex_str
    
        
        
# DateSegments
def test_valid_dates():
    dates = [
        '20240305'
    ]
    for e in dates:
        trex_str = f'A$T.D:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex._get_nested_validation_messages()

def test_valid_times():
    times = [
        'T0102', 'T010203', 'T010203.456'
    ]
    for e in times:
        trex_str = f'A$T.D:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex._get_nested_validation_messages()
    
def test_valid_datetimes():
    datetimes = [
        '20240305T0102', '20240305T010203', '20240305T010203', '20240305T010203.456'
    ]
    for e in datetimes:
        trex_str = f'A$T.D:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex._get_nested_validation_messages()
        
def test_invalid_dates_format():
    dates = [
        '2024030'
    ]
    for e in dates:
        trex_str = f'A$T.D:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex.is_valid
            
            
def test_invalid_dates():
    dates = [
        '20241331', '20240000'
    ]
    for e in dates:
        trex_str = f'A$T.D:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex.is_valid
            
            
def test_invalid_times_format():
    times = [
        'T2561'
    ]
    for e in times:
        trex_str = f'A$T.D:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex.is_valid
    


# BoolSgments
def test_valid_bool():
    b = [
        'T', 'F'
    ]
    for e in b:
        trex_str = f'A$T.B:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex._get_nested_validation_messages()
        
def test_invalid_bool():
    b = [
        '1', '0', 'TRUE', 'FALSE'
    ]
    for e in b:
        trex_str = f'A$T.B:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex.is_valid
            
            
            
# Alphanumeric Segment
def test_valid_alphanumeric():
    b = [
        'ABCDEFGHIJKLMNOPQRSTUVW012345678.-', 
    ]
    for e in b:
        trex_str = f'A$T.A:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex._get_nested_validation_messages()
        
def test_invalid_alphanumeric():
    b = [
        'a', '£', '<', 'ABCDeFGh'
    ]
    for e in b:
        trex_str = f'A$T.A:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex.is_valid



# Text Segment
def test_valid_text():
    b = [
        'ABCDEFGHIJKLMNOPQRSTUVW012345678', 
        'ABCD'
    ]
    for e in b:
        trex_str = f'A$T.T:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex._get_nested_validation_messages()
        assert trex.get_segment('A').value == e
          
def test_invalid_text():
    b = [
        'a', '£', '<', 'ABCDeFGh', 'ABCDEFGHIJKLMNOPQRSTUVW012345678.-'
    ]
    for e in b:
        trex_str = f'A$T.X:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex.is_valid
                   

      
# Binary Segment
def test_valid_binary():
    b = [
        'ABCDEFGHIJKLMNOPQRSTUVW012345678'
    ]
    for e in b:
        trex_str = f'A$T.X:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex._get_nested_validation_messages()
        
def test_invalid_binary():
    b = [
        'a', '£', '<', 'ABCDeFGh', 'ABCDEFGHIJKLMNOPQRSTUVW012345678.-'
    ]
    for e in b:
        trex_str = f'A$T.X:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex.is_valid
            
            
# Error Segment
def test_valid_error():
    b = [
        'ABCDEFGHIJKLMNOPQRSTUVW012345678.-'
    ]
    for e in b:
        trex_str = f'A$E:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex._get_nested_validation_messages()
        
def test_invalid_error():
    b = [
        'a', '£', '<', 'ABCDeFGh'
    ]
    for e in b:
        trex_str = f'A$E:{e}'
        trex = trex_deserialization_helper(trex_str)
        assert not trex.is_valid
            
            
# Table
def test_valid_table():
    tab = 'TAB$$C-0$T.A:C.1$T.B::TRUE:T::FALSE:F'
    trex = trex_deserialization_helper(tab)
    assert trex.is_valid
    t = trex.segments[0]
    assert isinstance(t, TableSegment)
    assert t.column_headers[0].key == 'C-0'
    assert t.column_headers[0].type == 'T.A'
    assert t.column_headers[1].key == 'C.1'
    assert t.column_headers[1].type == 'T.B'
    assert len(t.data) == 2
    assert [e.value for e in t.data[0]] == ['TRUE', 'T']
    assert [e.value for e in t.data[1]] == ['FALSE', 'F']
    
def test_invalid_header_keys():
    tab = 'TAB$$C£0$T.A:C1$T.B::TRUE:T::FALSE:F' # character £ in key
    trex = trex_deserialization_helper(tab)
    assert not trex.is_valid
        
def test_valid_header_types():
    d = [
        ('T.D', '20240101'), 
        ('T.B', 'T'), 
        ('T.A', 'ABC'),
        ('T.T', 'ABC'), 
        ('T.X', 'ABC'),
        ('E', 'ABC'), 
        ('HUR', '1'),
        ('C63', '2')
        ]
    for e in d:
        tab = f'TAB$$A${e[0]}::{e[1]}'
        trex = trex_deserialization_helper(tab)
        assert  trex.is_valid
        
def test_invalid_header_types():
    types = ['T.Q', 'T.', 'HURR', 'W70']
    for t in types:
        tab = f'TAB$$A${t}::V'
        trex = trex_deserialization_helper(tab)
        assert not trex.is_valid
            
def test_size_mismatch():
    tab = 'TAB$$C0$T.A:C1$T.B:C2$C63::TRUE:T::FALSE:T:1' #row 0 has only 2 elements
    trex = trex_deserialization_helper(tab)
    assert not trex.is_valid
        
def test_type_mismatch():
    tab = 'TAB$$C0$T.A:C1$T.B::TRUE:TRUE::FALSE:T' #element (0,1) has wrong type. should be boolean (T or F) but is text
    trex = trex_deserialization_helper(tab)
    assert not trex.is_valid


# Empty (Null) Values - a segment's value MAY be empty regardless of type
def test_empty_value_valid_for_every_type():
    types = ['HUR', 'C62', 'T.D', 'T.B', 'T.A', 'T.T', 'T.X', 'E']
    for type_ in types:
        trex_str = f'A${type_}:'
        trex = trex_deserialization_helper(trex_str)
        assert trex.is_valid, f"empty value should be valid for type {type_}"
        seg = trex.get_segment('A')
        assert seg.value == ''
        assert trex.serialize() == trex_str


def test_empty_date_value_does_not_default_to_midnight():
    # an empty T.D value means "not defined", not "00:00:00"
    trex = trex_deserialization_helper('A$T.D:')
    assert trex.is_valid
    seg = trex.get_segment('A')
    assert seg._date_time_dict is None


def test_empty_value_segment_ignored_by_other_types_validation():
    # an empty value must not accidentally trip a type's normal character-set/format checks
    trex_str = 'A$T.A:+B$T.B:+C$HUR:'
    trex = trex_deserialization_helper(trex_str)
    assert trex.is_valid
    assert trex.serialize() == trex_str


# Table empty cells
def test_table_empty_cell_first_element():
    # exact example from the T-REX spec: pH could not be measured for the middle row
    tab = 'TIT$$VOL$MLT:PH$C62:::2.44::4.0:1.00::8.0:4.33'
    trex = trex_deserialization_helper(tab)
    assert trex.is_valid
    t = trex.segments[0]
    assert len(t.data) == 3
    assert [e.value for e in t.data[0]] == ['', '2.44']
    assert [e.value for e in t.data[1]] == ['4.0', '1.00']
    assert [e.value for e in t.data[2]] == ['8.0', '4.33']
    assert trex.serialize() == tab
    
def test_table_empty_cell_last_column():
    # exact example from the T-REX spec: pH could not be measured for the middle row
    tab = 'TIT$$VOL$MLT:PH$C62::0.0:2.44::4.0:::8.0:4.33'
    trex = trex_deserialization_helper(tab)
    assert trex.is_valid
    t = trex.segments[0]
    assert len(t.data) == 3
    assert [e.value for e in t.data[0]] == ['0.0', '2.44']
    assert [e.value for e in t.data[1]] == ['4.0', '']
    assert [e.value for e in t.data[2]] == ['8.0', '4.33']
    assert trex.serialize() == tab


def test_table_empty_cell_first_column():
    tab = 'TIT$$VOL$MLT:PH$C62::0.0:2.44:::4.33'
    trex = trex_deserialization_helper(tab)
    assert trex.is_valid
    t = trex.segments[0]
    assert len(t.data) == 2
    assert [e.value for e in t.data[0]] == ['0.0', '2.44']
    assert [e.value for e in t.data[1]] == ['', '4.33']
    assert trex.serialize() == tab
    
    
def test_table_empty_cell_llast_element():
    # exact example from the T-REX spec: pH could not be measured for the middle row
    tab = 'TIT$$VOL$MLT:PH$C62::0.0:2.44::4.0:1.00::8.0:'
    trex = trex_deserialization_helper(tab)
    assert trex.is_valid
    t = trex.segments[0]
    assert len(t.data) == 3
    assert [e.value for e in t.data[0]] == ['0.0', '2.44']
    assert [e.value for e in t.data[1]] == ['4.0', '1.00']
    assert [e.value for e in t.data[2]] == ['8.0', '']
    assert trex.serialize() == tab


def test_table_malformed_row_size_not_masked_by_empty_values():
    # row 0 has 3 cells against a 2-column header - the token counts happen
    # to still divide evenly into 2-cell rows, so this must not be silently
    # reinterpreted as a well-formed table with values shifted around.
    tab = 'TAB$$C0$T.A:C1$T.A::A:B:C::D'
    trex = trex_deserialization_helper(tab)
    assert not trex.is_valid


def test_table_roundtrip_with_empty_cells_in_various_positions():
    # stress the row/boundary splitting: empty last cell, empty first cell, both cells
    # empty, and several such rows back to back - constructed programmatically and
    # round-tripped through serialize/deserialize rather than hand-counted colons.
    from labfreed.trex.table_segment import ColumnHeader, TableRow
    from labfreed.trex.trex_base_models import NumericValue

    headers = [ColumnHeader(key='A', type='C62'), ColumnHeader(key='B', type='C62')]
    row_values = [
        ['1', '2'],
        ['3', ''],
        ['', '4'],
        ['', ''],
        ['5', '6'],
        ['', ''],
        ['7', ''],
        ['', '8'],
    ]
    rows = [TableRow([NumericValue(value=v) for v in r]) for r in row_values]
    table = TableSegment(key='TAB', column_headers=headers, data=rows)

    trex_str = table.serialize()
    reparsed = trex_deserialization_helper(trex_str)
    assert reparsed.is_valid
    t = reparsed.segments[0]
    assert [[c.value for c in row] for row in t.data] == row_values
    assert reparsed.serialize() == trex_str


def test_table_single_row_single_column_all_empty():
    tab = 'TAB$$A$T.A::'
    trex = trex_deserialization_helper(tab)
    assert trex.is_valid
    t = trex.segments[0]
    assert len(t.data) == 1
    assert [e.value for e in t.data[0]] == ['']
    assert trex.serialize() == tab

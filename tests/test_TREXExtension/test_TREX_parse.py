import re
import pytest

from labfreed.TREX.data_model import *
from labfreed.TREX.parse import _from_trex_string, TREX_Parser

from labfreed.validation import LabFREEDValidationError

parser = TREX_Parser()

    
def test_trex_parse():
    trex_str = 'SUM$TREX/A$T.A:ASDFAS+B$T.B:T'
    trex = parser.parse_trex_str(trex_str)
    assert trex.name == 'SUM'
    assert trex.type == 'TREX'
    seg = trex.segments
    assert trex.get_segment('A').type == 'T.A'
    assert trex.get_segment('A').value == 'ASDFAS'
    assert trex.get_segment('B').type == 'T.B'
    assert trex.get_segment('B').value == 'T'
    
    
    
    
# Segment Key   
def test_invalid_keys():
    trex_str = '£TIM$HUR:1'
    with pytest.raises(LabFREEDValidationError) as e:
        trex = parser.parse_trex_str(trex_str, name="A")
        
    trex_str = 'tImE$HUR:1'
    with pytest.raises(LabFREEDValidationError) as e:
        trex = parser.parse_trex_str(trex_str, name="A")


# Numeric Segment
def test_numeric_segment_valid():
    trex_str ='TIME$HUR:25.0'
    trex = parser.parse_trex_str(trex_str, name="A")
    assert trex.data == trex_str
    
    trex_str ='TIME$HUR:25'
    trex = parser.parse_trex_str(trex_str, name="A")
    assert trex.data == trex_str
    
    trex_str ='TIME$HUR:-25.0'
    trex = parser.parse_trex_str(trex_str, name="A")
    assert trex.data == trex_str
    
    trex_str ='TIME$HUR:-25'
    trex = parser.parse_trex_str(trex_str, name="A")
    assert trex.data == trex_str
    
def test_numeric_segment_invalid_values():
    with pytest.raises(ValueError):
        trex_str ='TIME$HUR:A'
        trex = parser.parse_trex_str(trex_str, name="A")
        assert trex.data == trex_str
    
    with pytest.raises(ValueError):
        trex_str ='TIME$HUR:1.1.1'
        trex = parser.parse_trex_str(trex_str, name="A")
        assert trex.data == trex_str
        
def test_numeric_segment_invalid_unit():
    with pytest.raises(ValueError):
        trex_str ='TIME$HIP:A'
        trex = parser.parse_trex_str(trex_str, name="A")
        assert trex.data == trex_str
    
        
        
# DateSegments
def test_valid_dates():
    dates = [
        '20240305'
    ]
    for e in dates:
        trex = parser.parse_trex_str(f'A$T.D:{e}', name='A')
        assert not trex.get_nested_validation_messages()

def test_valid_times():
    times = [
        'T0102', 'T010203', 'T010203.456'
    ]
    for e in times:
        trex = parser.parse_trex_str(f'A$T.D:{e}', name='A')
        assert not trex.get_nested_validation_messages()
    
def test_valid_datetimes():
    datetimes = [
        '20240305T0102', '20240305T010203', '20240305T010203', '20240305T010203.456'
    ]
    for e in datetimes:
        trex = parser.parse_trex_str(f'A$T.D:{e}', name='A')
        assert not trex.get_nested_validation_messages()
        
def test_invalid_dates_format():
    dates = [
        '2024030'
    ]
    for e in dates:
        with pytest.raises(ValueError):
            trex = parser.parse_trex_str(f'A$T.D:{e}', name='A')
            
            
def test_invalid_dates():
    dates = [
        '20241331', '20240000'
    ]
    for e in dates:
        with pytest.raises(ValueError):
            trex = parser.parse_trex_str(f'A$T.D:{e}', name='A')
            
            
def test_invalid_times_format():
    times = [
        'T2561'
    ]
    for e in times:
        with pytest.raises(ValueError):
            trex = parser.parse_trex_str(f'A$T.D:{e}', name='A')
    


# BoolSgments
def test_valid_bool():
    b = [
        'T', 'F'
    ]
    for e in b:
        trex = parser.parse_trex_str(f'A$T.B:{e}', name='A')
        assert not trex.get_nested_validation_messages()
        
def test_invalid_bool():
    b = [
        '1', '0', 'TRUE', 'FALSE'
    ]
    for e in b:
        with pytest.raises(ValueError):
            trex = parser.parse_trex_str(f'A$T.B:{e}', name='A')
            
            
            
# Alphanumeric Segment
def test_valid_alphanumeric():
    b = [
        'ABCDEFGHIJKLMNOPQRSTUVW012345678.-', 
    ]
    for e in b:
        trex = parser.parse_trex_str(f'A$T.A:{e}', name='A')
        assert not trex.get_nested_validation_messages()
        
def test_invalid_alphanumeric():
    b = [
        'a', '£', '<', 'ABCDeFGh'
    ]
    for e in b:
        with pytest.raises(ValueError):
            trex = parser.parse_trex_str(f'A$T.A:{e}', name='A')


# Text Segment
def test_valid_text():
    b = [
        'ABCDEFGHIJKLMNOPQRSTUVW012345678', 
    ]
    for e in b:
        trex = parser.parse_trex_str(f'A$T.T:{e}', name='A')
        assert not trex.get_nested_validation_messages()
        
def test_invalid_text():
    b = [
        'a', '£', '<', 'ABCDeFGh', 'ABCDEFGHIJKLMNOPQRSTUVW012345678.-'
    ]
    for e in b:
        with pytest.raises(ValueError):
            trex = parser.parse_trex_str(f'A$T.T:{e}', name='A')

      
# Binary Segment
def test_valid_binary():
    b = [
        'ABCDEFGHIJKLMNOPQRSTUVW012345678', 
    ]
    for e in b:
        trex = parser.parse_trex_str(f'A$T.X:{e}', name='A')
        assert not trex.get_nested_validation_messages()
        
def test_invalid_binary():
    b = [
        'a', '£', '<', 'ABCDeFGh', 'ABCDEFGHIJKLMNOPQRSTUVW012345678.-'
    ]
    for e in b:
        with pytest.raises(ValueError):
            trex = parser.parse_trex_str(f'A$T.X:{e}', name='A')
            
            
# Error Segment
def test_valid_error():
    b = [
        'ABCDEFGHIJKLMNOPQRSTUVW012345678.-', 
    ]
    for e in b:
        trex = parser.parse_trex_str(f'A$E:{e}', name='A')
        assert not trex.get_nested_validation_messages()
        
def test_invalid_error():
    b = [
        'a', '£', '<', 'ABCDeFGh'
    ]
    for e in b:
        with pytest.raises(ValueError):
            trex = parser.parse_trex_str(f'A$E:{e}', name='A')
            
            
# Table
def test_valid_table():
    tab = 'TAB$$C-0$T.A:C.1$T.B::TRUE:T::FALSE:F'
    trex = parser.parse_trex_str(tab, name='A')
    assert not trex.get_errors()
    t = trex.segments[0]
    assert isinstance(t, TREX_Table)
    assert t.column_headers[0].key == 'C-0'
    assert t.column_headers[0].type == 'T.A'
    assert t.column_headers[1].key == 'C.1'
    assert t.column_headers[1].type == 'T.B'
    assert len(t.data) == 2
    assert [e.value for e in t.data[0]] == ['TRUE', 'T']
    assert [e.value for e in t.data[1]] == ['FALSE', 'F']
    
def test_invalid_header_keys():
    tab = 'TAB$$C£0$T.A:C1$T.B::TRUE:T::FALSE:F' # character £ in key
    with pytest.raises(LabFREEDValidationError):
        trex = parser.parse_trex_str(tab, name='A')
        
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
        trex = parser.parse_trex_str(tab, name='A')
        assert not trex.get_errors()
        
def test_invalid_header_types():
    types = ['T.Q', 'T.', 'HURR', 'W70']
    for t in types:
        tab = f'TAB$$A${t}::V'
        with pytest.raises(LabFREEDValidationError):
            trex = parser.parse_trex_str(tab, name='A')
            
def test_size_mismatch():
    tab = 'TAB$$C0$T.A:C1$T.B:C2$C63::TRUE:T::FALSE:T:1' #row 0 has only 2 elements
    with pytest.raises(LabFREEDValidationError):
        trex = parser.parse_trex_str(tab, name='A')
        
def test_type_mismatch():
    tab = 'TAB$$C0$T.A:C1$T.B::TRUE:TRUE::FALSE:T' #element (0,1) has wrong type. should be boolean (T or F) but is text 
    with pytest.raises(LabFREEDValidationError):
        trex = parser.parse_trex_str(tab, name='A')
        
            
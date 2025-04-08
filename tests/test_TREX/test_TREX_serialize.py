import re
import pytest

from labfreed.TREX.data_model import *
from labfreed.TREX.parse import _from_trex_string, TREX_Parser

from labfreed.validation import LabFREEDValidationError

parser = TREX_Parser()

    
def test_parse_followed_by_serialization_has_no_effect():
    d = [
        'DATE$T.D:20250101',
        'BOOL$T.B:T',
        'ALPHANUM$T.A:ABC',
        'TXT$T.T:ABCD',
        'BIN$T.X:ABDF',
        'ERR$E:123',
        'DUR$HUR:10',
        'TAB$$C-0$T.A:C.1$T.B::TRUE:T::FALSE:F'        
    ]
    for trex_str in d:
        trex = parser.parse_trex_str(trex_str, name='A')
        assert trex_str == trex.data
        
    trex_str = '+'.join(d)
    trex = parser.parse_trex_str(trex_str, name='A')
    assert trex_str == trex.data
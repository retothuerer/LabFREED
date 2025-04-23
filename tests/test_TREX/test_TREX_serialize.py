
from labfreed.trex import TREX

    
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
        trex = TREX.deserialize(trex_str)
        assert trex_str == trex.serialize()
        
    trex_str = '+'.join(d)
    trex = TREX.deserialize(trex_str)
    assert trex_str == trex.serialize()
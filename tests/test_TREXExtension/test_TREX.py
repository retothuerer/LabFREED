import re
import pytest

from labfreed.TREXExtension.data_model import TREX
from labfreed.TREXExtension.parse import from_trex_string


def test_all():
    d = " UNITHOUR$HUR:12\
        + UNITNONE$C62:89\
        + TXT$T.A:TXT\
        + TRUE$T.B:T"

    data_in = re.sub(r"\s+", "", d)
    trex = TREX.from_spec_fields(name="TST", type="TREX", data=data_in)
    data_out = trex.data
    assert data_in == data_out
    
    
def test_trex_parse():
    trex_str = 'SUM$TREX/A$T.A:ASDFAS+B$T.B:T'
    trex = from_trex_string(trex_str)
    assert trex.name == 'SUM'
    assert trex.type == 'TREX'
    seg = trex.segments
    assert seg['A'].type == 'T.A'
    assert seg['A'].value == 'ASDFAS'
    assert seg['B'].type == 'T.B'
    assert seg['B'].value == 'T'

    
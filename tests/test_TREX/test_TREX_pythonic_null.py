import pytest

from labfreed.trex import TREX
from labfreed.trex.pythonic.pyTREX import pyTREX


def test_empty_value_becomes_none_for_every_type():
    trex_str = 'NUM$HUR:+DATE$T.D:+BOOL$T.B:+ALPHA$T.A:+TXT$T.T:+BIN$T.X:+ERR$E:'
    trex = TREX.deserialize(trex_str)
    assert trex.is_valid
    py = pyTREX.from_trex(trex)
    for key in ['NUM', 'DATE', 'BOOL', 'ALPHA', 'TXT', 'BIN', 'ERR']:
        assert py[key] is None, f"{key} should decode to None"


def test_table_empty_cell_becomes_none():
    tab = 'TIT$$VOL$MLT:PH$C62::0.0:2.44::4.0:::8.0:4.33'
    trex = TREX.deserialize(tab)
    assert trex.is_valid
    py = pyTREX.from_trex(trex)
    table = py['TIT']
    assert table.data[0][1].value == 2.44
    assert table.data[1][1] is None
    assert table.data[2][1].value == 4.33

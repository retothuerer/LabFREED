import pytest

from labfreed.trex.trex import Spec_T_REX, TREX
from labfreed.trex.facade.pyTREX import T_REX, pyTREX


# Covers the trex/facade rename: TREX (spec-literal core) -> Spec_T_REX, with TREX kept
# as a deprecated alias; pyTREX (wrapper) -> T_REX, with pyTREX kept as a deprecated
# alias. See design-choices.md for the "flip the plain name onto the wrapper" reasoning.

def test_spec_t_rex_is_the_renamed_core_type():
    trex_str = 'NUM$HUR:5'
    t = Spec_T_REX.deserialize(trex_str)
    assert isinstance(t, Spec_T_REX)
    assert t.serialize() == trex_str


def test_old_trex_name_still_works_and_warns():
    trex_str = 'NUM$HUR:5'
    with pytest.deprecated_call():
        t = TREX.deserialize(trex_str)
    # deprecated old name must still behave identically and satisfy the new type
    assert isinstance(t, TREX)
    assert isinstance(t, Spec_T_REX)
    assert t.serialize() == trex_str


def test_old_trex_direct_construction_warns():
    with pytest.deprecated_call():
        TREX(segments=[])


def test_t_rex_is_the_renamed_wrapper_type():
    segments = {'X': 5}
    py = T_REX(segments)
    assert isinstance(py, T_REX)
    trex = py.to_trex()
    assert isinstance(trex, Spec_T_REX)


def test_old_pytrex_name_still_works_and_warns():
    with pytest.deprecated_call():
        py = pyTREX({'X': 5})
    assert isinstance(py, pyTREX)
    assert isinstance(py, T_REX)
    trex = py.to_trex()
    assert isinstance(trex, Spec_T_REX)

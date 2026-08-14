'''
to_trex()/from_trex() renamed to to_trex_spec()/from_trex_spec() - the old names
made sense when the friendly facade class was itself named pyTREX ("this
pythonic wrapper, converted to a trex"); now that it's named T_REX, both read
as near-tautological, and the new names say what they actually produce/consume
(a Spec_T_REX). Old names kept as deprecated, functioning shims for one version.

New T_REX.serialize()/T_REX.deserialize(s) become the everyday "dict in/out,
wire string out/in" entry point, matching Spec_T_REX's own verb pair exactly -
to_trex_spec()/from_trex_spec() become the rarely-touched bridging step, still
needed for e.g. handing a Spec_T_REX directly to TREX_Extension.trex.
'''
import pytest

from labfreed.trex.trex import Spec_T_REX
from labfreed.trex.facade.t_rex import T_REX


TREX_STR = "NUM$HUR:5"


def test_to_trex_spec_is_the_renamed_method():
    t = T_REX({"NUM": 5}).to_trex_spec()
    assert isinstance(t, Spec_T_REX)
    assert t.get_segment("NUM").type == "HUR"


def test_old_to_trex_name_still_works_and_warns():
    py = T_REX({"NUM": 5})
    with pytest.deprecated_call():
        t = py.to_trex()
    assert isinstance(t, Spec_T_REX)
    assert t.serialize() == py.to_trex_spec().serialize()


def test_from_trex_spec_is_the_renamed_classmethod():
    py = T_REX.from_trex_spec(Spec_T_REX.deserialize(TREX_STR))
    assert isinstance(py, T_REX)
    assert py["NUM"] == 5


def test_old_from_trex_name_still_works_and_warns():
    with pytest.deprecated_call():
        py = T_REX.from_trex(Spec_T_REX.deserialize(TREX_STR))
    assert isinstance(py, T_REX)
    assert py["NUM"] == 5


def test_serialize_matches_to_trex_spec_then_serialize():
    py = T_REX({"NUM": 5})
    assert py.serialize() == py.to_trex_spec().serialize()


def test_deserialize_matches_from_trex_spec_of_the_parsed_string():
    py = T_REX.deserialize(TREX_STR)
    assert py["NUM"] == 5
    assert py == T_REX.from_trex_spec(Spec_T_REX.deserialize(TREX_STR))


def test_serialize_deserialize_round_trips():
    original = T_REX({"NUM": 5, "OK": True})
    assert T_REX.deserialize(original.serialize()) == original

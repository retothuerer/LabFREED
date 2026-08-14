'''
Explicit-type wrapper family for T_REX's dict facade: Alphanumeric/Text/Numeric/
Bool/Date, one per wire type, so any entry's type can be stated instead of
always inferred from the Python value's runtime type. Auto-detection stays the
default fallback for bare Python values - nothing about existing behavior
changes.

Only string values are genuinely ambiguous today (T.A vs. T.T, decided by a
regex charset check, duplicated across the top-level dict value and DataTable
column/cell inference) - Numeric/Bool/Date complete the family for symmetry
per explicit decision, even though bare int/float/bool/date already dispatch
unambiguously.

Text is NOT a base36 alias, despite an earlier draft of this design assuming
it could be: `base36` validates its input as *already* base36-encoded
(`[A-Z0-9]*`), so `base36("free text")` would raise - it's a pre-encoded-data
escape hatch, kept exactly as-is. Text takes ordinary human-readable text and
encodes it to base36 internally at serialization time, mirroring what the
existing str-auto-detect fallback already does for a non-alphanumeric string,
just made explicit/opt-in.
'''
import pytest

from labfreed.trex.facade.t_rex import T_REX
from labfreed.trex.facade.data_table import DataTable
from labfreed.trex.facade.typed_values import Alphanumeric, Text, Numeric, Bool, Date
from labfreed.utilities.base36 import to_base36


def test_alphanumeric_forces_ta_and_validates_eagerly():
    t = T_REX({"BATCH": Alphanumeric("A123")}).to_trex_spec()
    seg = t.get_segment("BATCH")
    assert seg.type == "T.A"
    assert seg.value == "A123"


def test_alphanumeric_rejects_invalid_charset_at_construction():
    with pytest.raises(ValueError):
        Alphanumeric("lower case")


def test_text_encodes_ordinary_text_to_base36_and_forces_tt():
    t = T_REX({"NOTE": Text("free text")}).to_trex_spec()
    seg = t.get_segment("NOTE")
    assert seg.type == "T.T"
    assert seg.value == to_base36("free text").root


def test_base36_still_requires_already_encoded_data_and_is_unchanged():
    ''' base36 is not Text - it's the pre-encoded-data escape hatch, unchanged by this
    feature. Passing raw (unencoded) text to it must still fail exactly as before. '''
    from labfreed.utilities.base36 import base36
    with pytest.raises(ValueError):
        base36(root="free text")


def test_bare_string_auto_detection_is_unchanged():
    alphanumeric_auto = T_REX({"BATCH": "A123"}).to_trex_spec().get_segment("BATCH")
    alphanumeric_explicit = T_REX({"BATCH": Alphanumeric("A123")}).to_trex_spec().get_segment("BATCH")
    assert alphanumeric_auto.type == alphanumeric_explicit.type == "T.A"

    text_auto = T_REX({"NOTE": "free text"}).to_trex_spec().get_segment("NOTE")
    text_explicit = T_REX({"NOTE": Text("free text")}).to_trex_spec().get_segment("NOTE")
    assert text_auto.type == text_explicit.type == "T.T"
    assert text_auto.value == text_explicit.value


def test_numeric_bool_date_wrappers_are_equivalent_to_the_bare_python_type():
    ''' No real ambiguity exists for these types - the wrappers exist for symmetry/
    explicitness only, and must produce identical results to the bare value. '''
    import datetime as dt

    assert T_REX({"X": Numeric(5)}).to_trex_spec().serialize() == T_REX({"X": 5}).to_trex_spec().serialize()
    assert T_REX({"X": Bool(True)}).to_trex_spec().serialize() == T_REX({"X": True}).to_trex_spec().serialize()
    d = dt.date(2024, 2, 22)
    assert T_REX({"X": Date(d)}).to_trex_spec().serialize() == T_REX({"X": d}).to_trex_spec().serialize()


def test_explicit_type_extends_to_data_table_columns():
    ''' The same explicit-type override must be honored inside a DataTable column, not
    just at the top level - this is the "closes the ambiguity for tables too" half of
    the shared-dispatch-helper fix. '''
    table = DataTable(col_names=["CODE"], data=[[Alphanumeric("A1")], [Alphanumeric("B2")]])
    seg = T_REX({"BATCHES": table}).to_trex_spec().get_segment("BATCHES")
    assert seg.column_types == ["T.A"]
    assert [v.value for v in seg.column_data("CODE")] == ["A1", "B2"]

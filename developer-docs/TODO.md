# TODO

General backlog of things worth picking up later - not scoped to any one topic. Ideas
that relate to an entry in [`design-choices.md`](design-choices.md) should cross-link
to it (both directions), but this file isn't exclusively for design-choice follow-ups -
anything worth not losing track of belongs here.

---

## Use `ValidationInfo.context` to replace the manual nested-message tree-walk

Related to: ["Non-fatal, severity-tiered validation instead of plain pydantic
errors"](design-choices.md#non-fatal-severity-tiered-validation-instead-of-plain-pydantic-errors)

Idea: instead of `self._validation_messages` (a `PrivateAttr` on every
`LabFREED_BaseModel` instance) plus `_get_nested_validation_messages()` walking the
object graph afterward, validators could append to a shared `context['messages']`
list/dict passed into `Model.model_validate(data, context={...})`. Confirmed
empirically (pydantic 2.13.4) that pydantic threads the *same* context object down into
nested models' validators automatically within one `model_validate()` call - no manual
recursion needed, and it survives even if validation later raises, since the caller
still holds a reference to that mutable object.

Blocker: this only works when construction goes through `model_validate()` /
`model_validate_json()`. A plain `Model(...)` call never receives it - confirmed
`info.context` is `None` even when passing `context=` as a kwarg to `__init__` (silently
treated as an unrecognized field under default `extra='ignore'`, no error raised).
Before attempting this, audit whether `LabFREED_BaseModel` subclasses are ever
constructed via plain `Model(...)` instead of `.model_validate(...)` anywhere in the
codebase - including by consumers of the package, not just internally. If so, this
would silently drop messages with no error, which is worse than the current recursive
walk it would replace.

---

## ~~Fix table row parsing to handle empty cell values~~ (fixed, see below)

Fixed on branch `trex-nullable-empty-values`, alongside the rest of the
`nullable-empty-values` T-REX spec adaptation. The chunk-by-`len(headers)` sketch
below turned out to have a gap: it only checked that the *total* token count divided
evenly into `n_cols`-sized rows, which is necessary but not sufficient — a malformed
table whose token count coincidentally still divides evenly (e.g. one row with an
extra cell and the next with one too few) would silently misattribute values instead
of being caught by `TableSegment._validate_sizes`. The actual fix in
`labfreed/trex/table_segment.py` (`_split_table_rows`) walks the body value-by-value
instead, using the running per-row count to know at every position whether the next
colon must be a plain separator (row not yet at `len(headers)` values) or the start of
the `::` row separator (row already complete) — falling back to the old naive
`'::'`-split only when that expectation is violated, so existing malformed-input
detection (`test_size_mismatch`, `test_type_mismatch`) still behaves as before. See
tests in `tests/test_TREX/test_TREX_parse.py`
(`test_table_empty_cell_last_column`/`_first_column`/`test_table_roundtrip_with_empty_cells_in_various_positions`).

Also fixed as part of the same branch: the `value_segments.py` and `table_segment.py`
deserialization regexes both required at least one character for the value/body
capture group (`.+`), which raised (rather than just failing validation) on any
legitimately-empty value or single-cell-empty-table body; both are now `.*`.

---

## `to_trex()` doesn't write `None` back as an empty value of the right type

Related to: ["Empty T-REX values decode to Python `None` in the pythonic
layer"](design-choices.md#empty-t-rex-values-decode-to-python-none-in-the-pythonic-layer)

The `trex-nullable-empty-values` branch fixed the *read* direction
(`_trex_value_to_python_type`/`_trex_segment_to_python_type`): any empty T-REX value now
decodes to Python `None`, for scalars and `DataTable` cells alike. The *write* direction
(`pyTREX.to_trex()`) wasn't touched and still has a pre-existing quirk: a `None` cell
inside a `DataTable` gets serialized via `_error_value_from_python_type(None)` — i.e. an
`ErrorValue('-')` — regardless of the column's actual declared type (`h.type` is right
there in scope but unused for the `None` branch). For any column that isn't itself
error-typed, this cell would then fail `TableSegment._validate_data_types` (type
mismatch: header says e.g. `T.B`/a numeric unit, cell is an `ErrorValue`) — so a
round-trip of `DataTable(..., data=[[..., None, ...]])` through `to_trex()` and back
currently produces an invalid `TREX`, even though `DataTable.data`'s own type
(`Union[..., None]`) and `get_row_template` already treat `None` cells as first-class.

Fix direction: for a table cell, serialize `None` as an *empty* value of the column's
own declared type (`h.type`) instead of always falling back to `ErrorValue('-')` — e.g.
build via the same `_str_to_value_type(h.type, '')` helper `table_segment.py` already
uses for parsing. The scalar (non-table) `None` case is murkier: a bare top-level dict
value has no type annotation to infer a segment `type` from, so keeping the
`ErrorValue('-')` placeholder there may still be the least-bad option — flag this for
discussion rather than assuming the table fix generalizes.

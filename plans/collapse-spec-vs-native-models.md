# Plan: collapse spec model + native-Python wrapper into one class

Status: **parked, not started.** Came out of an architecture discussion on the `dev`
branch (2026-07-27), too big to do alongside the smaller folder/naming cleanups.

## Background

Building blocks that have a `python_convenience`/`pythonic` layer today do it by
maintaining two full parallel classes:

- a spec-exact model (e.g. `TREX`, made of `TREX_Segment` subclasses with
  spec-typed values: `NumericValue`, `DateValue`, UNECE unit codes, etc.)
- a native-Python wrapper (e.g. `pyTREX`, a `RootModel[dict[str, Quantity | datetime
  | ... | DataTable]]`) that converts to/from native Python types, and re-implements
  dict semantics (`__getitem__`, `keys`, `values`, `items`, ...) purely to proxy
  through to `.root`.

Same shape in `pac_attributes`: `Attribute` (spec) vs `pyAttribute` (native).

This came up because the `py`-prefix naming (`pyTREX` vs `TREX`, `pyAttribute` vs
`Attribute`) exists specifically to avoid a same-name class collision within one
package — not because of any real "pythonic" naming convention (there isn't one;
see conversation for the CPython C-API / PyQt-style precedent that the prefix
accidentally borrows from). Renaming doesn't remove the underlying reason two
classes need distinguishing in the first place: there are two classes representing
the same concept.

## Idea: one class, convenience accessors instead of a second class

Keep only the spec-exact model. Add methods that compute the native-Python view on
demand instead of a second stored/parallel representation:

```python
class TREX(LabFREED_BaseModel):
    segments: list[TREX_Segment] = Field(default_factory=list)

    @classmethod
    def deserialize(cls, data) -> Self: ...   # unchanged
    def serialize(self) -> str: ...            # unchanged
    def get_segment(self, key) -> TREX_Segment | None: ...  # unchanged

    def native(self, key: str):
        '''Value of one segment as its native Python type.'''
        seg = self.get_segment(key)
        return _segment_to_native(seg) if seg else None

    def to_native_dict(self) -> dict[str, Quantity | datetime | time | date | bool | str | base36 | DataTable]:
        '''All segments as a plain dict of native Python values.'''
        return {seg.key: _segment_to_native(seg) for seg in self.segments}

    @classmethod
    def from_native_dict(cls, values: dict) -> Self:
        '''Build a TREX from native Python values.'''
        return cls(segments=[_native_to_segment(k, v) for k, v in values.items()])
```

`_segment_to_native` / `_native_to_segment` are today's `_trex_segment_to_python_type`
and the big `isinstance` chain in `pyTREX.to_trex()`, moved to module-level functions
(in `trex.py` or a private `_native.py` next to it) instead of methods on a second
class.

Usage before/after:

```python
# before
pytrex = pyTREX.from_trex(trex)
weight = pytrex['WEIGHT']
# after
weight = trex.native('WEIGHT')

# before
trex = pyTREX({'WEIGHT': Quantity(value=67.89, unit='g')}).to_trex()
# after
trex = TREX.from_native_dict({'WEIGHT': Quantity(value=67.89, unit='g')})
```

Same treatment would apply to `pac_attributes`: `Attribute.native()` /
`.to_native_dict()` / `Attribute.from_native_dict()` instead of `pyAttribute`.

## Why this is worth doing

- Removes the naming-collision problem at the root (only one class per concept —
  nothing left to disambiguate with a prefix).
- Deletes the dict-proxy boilerplate (`__getitem__`/`__setitem__`/`keys`/`values`/
  `items`/`__contains__`/`__iter__`/`__len__` — 9 lines of pure passthrough in
  `pyTREX` alone).
- No second pydantic model with `arbitrary_types_allowed` to keep in sync with the
  spec model as the spec evolves.
- `.to_native_dict()` / `.from_native_dict()` mirrors pydantic's own `.model_dump()`
  shape — a recognizable idiom rather than a bespoke wrapper class.

## Tradeoffs / open questions

- Loses the automatic pydantic validation `RootModel[dict[str, Quantity | ...]]`
  gave for free when constructing from an arbitrary dict. In practice this may not
  matter much: the conversion is already manual `isinstance` dispatch either way.
- **Found along the way, independent bug worth fixing regardless of this plan:**
  `pyTREX.to_trex()`'s `isinstance` chain has no final `else: raise` — a value of
  an unsupported native type is currently silently dropped from the resulting
  `TREX` instead of raising. Should raise a clear `TypeError` instead.
- Naming for the "native dict" method needs to clearly avoid confusion with
  pydantic's own `.model_dump()` (spec-level serialization, not native-type
  conversion) — `to_native_dict()`/`from_native_dict()` was the working name during
  discussion, not finalized.
- No caching: `to_native_dict()` recomputes the whole dict every call, same as
  `pyTREX.from_trex(trex)` does today — not a regression, just noting it isn't free.
- This is a breaking API change for any existing consumer using `pyTREX`/
  `pyAttribute` directly — needs a deprecation path if this ships, not a
  drop-in replacement.

## Scope if/when this gets picked up

1. Prototype on `TREX` only first (smallest surface: `trex.py`,
   `trex/python_convenience/pyTREX.py`, `trex/python_convenience/quantity.py`,
   `trex/python_convenience/data_table.py`).
2. Run existing test suite (`tests/test_Quantity.py`,
   `tests/test_PAC_CAT/*`, generated tests) against the prototype before touching
   anything else.
3. Only generalize to `pac_attributes` (`Attribute`/`pyAttribute`) after the TREX
   prototype is validated.
4. Decide on a deprecation window for `pyTREX`/`pyAttribute` rather than deleting
   them outright, given they're public API today.

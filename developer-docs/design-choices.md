# Design choices

Non-obvious architectural and API decisions in this codebase, with the reasoning and
the alternative(s) that were considered and rejected. Reading the code tells you *what*
it does; this file is for *why* it's shaped this way, when that reasoning isn't obvious
from the implementation alone.

Add an entry whenever a decision like this gets made or (re-)discovered - see the
`design-choices` skill. Follow-up ideas that come up while documenting a choice, but
aren't worth acting on immediately, go in the general [`TODO.md`](TODO.md) instead,
cross-referenced back here.

---

## Non-fatal, severity-tiered validation instead of plain pydantic errors

**Decision:** `LabFREED_BaseModel` (`labfreed/labfreed_infrastructure.py`) adds its own
per-instance validation-message log (`ValidationMessage`, with levels
ERROR/WARNING/RECOMMENDATION/INFO) instead of relying on pydantic's own
`ValidationError`. Validators call `self._add_validation_message(...)` rather than
raising; `errors()` / `warnings()` / `is_valid` read the log back afterward, recursively
across nested models and computed fields (`_get_nested_validation_messages`). Nearly
every model in the package subclasses `LabFREED_BaseModel` rather than plain
`pydantic.BaseModel` as a result.

**Why:** Pydantic's validation is binary - a validator that raises aborts construction
entirely (`ValidationError`), so there's no instance left to attach non-fatal findings
to. There is no tier between "valid" and "doesn't exist." LabFREED needs exactly that
middle tier: e.g. a PAC-ID that's *valid but not recommended*, or a resolver config
entry with a soft issue that shouldn't block parsing the rest of a document.

**Alternatives considered / why not:**

- Plain pydantic `ValidationError` + `PydanticCustomError` - pydantic already
  aggregates multiple *fatal* field failures into one exception natively, but only for
  the raise-and-abort path. No way to keep a partially-valid instance around with
  attached soft issues once something raises.
- Python's `warnings.warn()` - a global/process-wide side channel, not scoped to a
  specific instance and not structured (no severity levels, no per-model traversal).
- `ValidationInfo.context` (passed via `Model.model_validate(data, context={...})`) -
  confirmed empirically (pydantic 2.13.4) that this *does* propagate automatically into
  nested models' own validators within a single `model_validate()` call, which could
  replace the manual `_get_nested_validation_messages()` tree-walk. Not adopted because
  it only works through `model_validate()` / `model_validate_json()` - a plain
  `Model(...)` call never sees it (confirmed: `info.context` stays `None` even when
  `context=` is passed as a kwarg to `__init__` - it's silently dropped as an
  unrecognized field under default `extra='ignore'`). Since models are constructed both
  ways across the codebase today, switching would silently lose messages wherever
  direct construction is used. See
  [`TODO.md`](TODO.md#use-validationinfocontext-to-replace-the-manual-nested-message-tree-walk).
- Pydantic's only built-in "warning" concept (`model_dump(warnings=...)`) is unrelated -
  it flags internal serialization type-mismatches, not user-defined domain warnings.

**Impact:** the cost of the above is that everything wanting soft-validation messages
must subclass `LabFREED_BaseModel` - there's no way to bolt this behavior onto a plain
`pydantic.BaseModel` after the fact.

*Investigated 2026-07-27.*

---

## Error-as-data T-REX segments instead of failing the whole parse

**Decision:** T-REX defines `E` as a genuine first-class segment type (`ErrorSegment` /
`ErrorValue` in `labfreed/trex/value_segments.py` and `trex_base_models.py`), alongside
the real value types (`T.D`, `T.B`, `T.A`, `T.T`, `T.X`, numeric/UNECE units). A segment
whose declared type is `E` deserializes into a normal, valid `ErrorSegment` node rather
than being rejected. `pyTREX.to_trex()` (`labfreed/trex/pythonic/pyTREX.py`) also
actively *constructs* one - e.g. a Python value of `None` becomes an `ErrorSegment`
rather than raising while building a T-REX from pythonic data.

**Why:** a T-REX is a flat sequence of independent key/value segments. Raising on the
first segment that can't be represented would throw away every other, perfectly valid
segment in the same string/object just because one entry was bad. Making "erroneous
value" a value shape of its own means the rest of the structure still round-trips, and
the error is localized to exactly the segment that has it - consistent with the same
"error is data, not an aborted construction" theme as the validation-message log above,
but solved at the parsing/shape level instead of the instance-metadata level.

**Alternatives considered / why not:** none recorded from this investigation - this
entry documents an existing decision found while surveying the codebase for similar
patterns, not a live investigation with rejected alternatives. Revisit if the original
rationale/PR is found.

*Investigated 2026-07-27 (documenting a pre-existing decision, not a new investigation).*

---

## `pac_id` depends on `pac_cat` / `well_known_extensions`, against the "obvious" layering

**Decision:** `PAC_Parser` (`labfreed/pac_id/url_parser.py`) and `PACID_Serializer`
(`labfreed/pac_id/url_serializer.py`) import `PAC_CAT` and the well-known extension
interpreters directly, even though `pac_cat` is conceptually a specialization built on
top of `pac_id` - the "obvious" dependency direction would be the reverse, with `pac_id`
knowing nothing about `pac_cat`. This is already called out explicitly in
`url_parser.py`'s own docstring:

> From a SW engineering perspective it would be best to have no dependencies from other
> modules to pac_id. However from a Python users convenience perspective it is better to
> have one place where a pac url can be parsed and magically the extensions are in a
> meaningful type (e.g. TREX in TREX aware format) and categories are known if possible.
> We have given priority to convenient usage and therefore chose to have dependencies
> from pac_id to pac_cat and well_known_extensions.

**Why:** without this, parsing a PAC-ID URL that happens to be a PAC-CAT would return a
plain `PAC_ID` with untyped identifier segments, and callers would need to know to
separately re-parse it as `PAC_CAT` (and separately ask extensions to interpret
themselves as TREX, etc.) to get useful types back. Centralizing that in one parser
entry point means `PAC_Parser.from_url()` / `PAC_ID.from_url()` "just works" and hands
back the most specific, meaningfully-typed object it can - at the cost of a layering
violation that a purist module graph wouldn't have.

**Alternatives considered / why not:** the clean alternative - `pac_id` staying fully
ignorant of `pac_cat` and extension interpreters, pushing the "give me the specific type"
step onto every caller - was rejected in favor of convenience, per the docstring above.

**Impact:** `pac_id` cannot be imported/used in isolation without pulling in `pac_cat`
and `well_known_extensions` - there's no lightweight "just the base PAC-ID parser"
import path. Keep this in mind if `pac_cat` or the extension interpreters ever need to
depend back on something in `pac_id` beyond what they already do - that would create an
import cycle, not just an awkward layering.

*Investigated 2026-07-27 (documenting a pre-existing, already self-explained decision).*

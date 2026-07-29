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

---

## Empty T-REX values decode to Python `None` in the pythonic layer

**Decision:** In `pyTREX._trex_value_to_python_type` (`labfreed/trex/pythonic/pyTREX.py`),
a T-REX value that's empty decodes to Python `None`, via a single check at the top of
the function (`if not v.value: return None`) rather than a per-type default. This
applies uniformly across every value type - `NumericSegment`/`Quantity`, `DateValue`,
`BoolValue`, `AlphanumericValue`, `TextValue`, `BinaryValue`, `ErrorValue` - and to
individual `DataTable` cells.

**Why:** The T-REX spec's `nullable-empty-values` branch defines an empty `value` as
"not defined," regardless of `type` - so the most faithful, least-surprising Python
representation is Python's own null value, not a type's zero-ish default (`0`, `False`,
`''`) which would look like real data, and not raising, which would make legitimately
empty, spec-compliant T-REX unrepresentable in the pythonic layer at all.
`DataTable.data`'s type (`Union[Quantity | ... | None]`) and `get_row_template` already
treated `None` cells as first-class before this change existed - the table-cell
decoding path (which used to construct `Quantity(value=e.value, ...)` directly from an
empty string) was the one place actually broken until this fix landed. See
[`TODO.md`](TODO.md#to_trex-doesnt-write-none-back-as-an-empty-value-of-the-right-type)
for the write-direction (`to_trex()`) counterpart, which this change does not cover.

**Alternatives considered / why not:**

- Returning each type's zero-ish default - this was already happening by accident for
  two types, not by design: an empty `T.D` silently became midnight (`time()` with no
  args, since the date/time regex's groups are all optional and matched empty), and an
  empty `T.B` silently fell through to an implicit `None` return only because a
  pre-existing bug in the bool branch constructed but never raised its `Exception`.
  Neither behavior was intentional and neither survives round-tripping distinctly from
  an actual midnight timestamp or a real boolean.
- Raising on decode - would make a spec-legal T-REX string (empty value for any type)
  impossible to convert via `pyTREX.from_trex`, defeating the point of adding
  nullability to the spec.

*Introduced 2026-07-28 on branch `trex-nullable-empty-values`, alongside the T-REX
grammar/parsing side of the same change (see the "table row parsing" entry in
[`TODO.md`](TODO.md)).*

---

## Empty `id segment`s (trailing/double `/`) are rejected, not normalized

**Decision (revised 2026-07-29 - see revision note below):** `IDSegment._validate_segment`
(`labfreed/pac_id/id_segment.py`) flags *any* empty `id segment` value as an ERROR-level
validation message - including the empty segment produced by a *repeated* `/` in an
`identifier` (e.g. `-MD/240:BAL500//21:12345` splits into an empty segment). This part is
unchanged. What changed: a single *trailing* `/` (e.g. `-MD/240:BAL500/21:12345/`) is no
longer treated as producing an empty segment at all - `PAC_Parser` now strips exactly one
trailing `/` before splitting into segments, so it contributes no segment (empty or
otherwise), and instead surfaces as a WARNING-level validation message rather than an
ERROR. A *doubled* trailing `/` (e.g. `.../21:12345//`) still produces a genuine empty
final segment and still hits the ERROR path below, unchanged.

**Why:** an `id segment` is defined (PAC-ID spec) as "a part of an `identifier` that
can stand on its own... used to organize `identifier`s." An empty value can't stand on
its own or organize anything - it's indistinguishable from "no segment at all," except
that it costs an extra `/`. Nothing in PAC-ID or PAC-CAT ever gives an empty segment
meaning: PAC-CAT's short notation infers keys from segment *position*, and an omitted
optional `category segment` is described as skipped outright, never represented as an
empty placeholder to preserve alignment. So an empty segment can only ever be an
accident - most commonly a trailing `/` a caller forgot to strip - and treating it as
a hard error surfaces that mistake immediately instead of silently accepting a
malformed identifier. (Confirmed even the PAC-CAT spec's own example table had one:
the "Instrument by Mettorius" row carried a stray trailing `/` until this was found
and fixed alongside this decision.)

**Alternatives considered / why not (original 2026-07-28 decision, double `/` only):**

- Silently strip a trailing/double `/` before parsing (mirroring the leading-`/` strip
  `_parse_id_segments` already does) - rejected because it would hide a caller bug
  (e.g. a URL-building mistake upstream) behind seemingly-successful parsing, with no
  trace that anything was off.
- Accept but downgrade to a WARNING/RECOMMENDATION-level message instead of ERROR -
  rejected for the same reason as above: an empty segment never carries legitimate
  meaning, so there's no "acceptable but non-ideal" middle ground the way there is for,
  say, a non-well-known `id segment key`.

**Impact:** callers that build `identifier` strings themselves (e.g. proxying a
third-party conversion service, as in `labfreed-webtools/instrument_demo/`) are
responsible for stripping any *doubled* trailing/inner `/` before calling
`PAC_ID.from_url()` - the library will not do it for them. A single trailing `/` is
handled by the library itself (see revision below), so callers no longer need to guard
against that specific, very common case themselves. The PAC-ID spec wording was also
tightened from "At least one `id segment` MUST be non-empty" (ambiguous - arguably
permitted some empty segments) to "No `id segment` may be empty," to match this
implementation behavior exactly.

**Revision, 2026-07-29 - single trailing `/` carved out:** the two alternatives above
were re-examined for the specific case of exactly one trailing `/` (not a doubled
`/`, which is still handled exactly as decided above) and adopted after all: a single
trailing `/` is now stripped before segment-splitting (so it produces no segment,
empty or otherwise) and surfaces as a WARNING rather than an ERROR; `pac_id.is_valid`
is `True` for this case. The earlier "no middle ground" reasoning still holds for a
*doubled* `/` (or one in the middle of the identifier) - that always produces a real
empty segment with no possible other meaning, and remains a hard ERROR. But a lone
trailing `/` is common enough real-world noise (e.g. a caller-built URL with an extra
separator) that maintainers decided it doesn't warrant surfacing as a hard error at
the core parsing layer - see `PAC-ID-Attributes' subject_id...` entry below for the
adjacent decision this narrows the gap with (that entry already tolerated this same
case one layer up, at the attribute-service boundary rather than in `PAC_ID` itself).
Downstream code that canonicalizes a valid id before using it as a lookup key (e.g.
`Dict_DataSource.attributes()`) needs to account for the canonical form no longer
matching a raw, as-stored key that still carries the stripped slash - fixed there by
falling back to a raw-string lookup when the canonical-key lookup misses.

*Investigated 2026-07-28 (double `/`), revised 2026-07-29 (single trailing `/`) -
originally prompted by a real trailing-`/` failure surfaced via
`bp_instrument_demo.py`'s PAC-Ninja conversion path.*

---

## PAC-ID-Attributes' `subject_id` accepts any IRI; the client never reserializes a string one through `PAC_ID`

**Decision:** `AttributeRequestData._validate_subject_id` (`api_data_models/request.py`)
treats `subject_id` as valid whenever it's a syntactically valid IRI (approximated via
`pydantic.AnyUrl`), and only downgrades "not a valid PAC-ID" to a WARNING - it no longer
requires a strict PAC-ID. Correspondingly, `AttributeClient.get_attributes()`
(`client/client.py`) stopped routing every `subject_id` through
`PAC_ID.from_url(...).to_url()`: a `PAC_ID` instance is still canonicalized via
`.to_url()` as before, but a plain `str` is sent to the server and compared against the
response's `id` completely as-is, with no PAC_ID parsing in between.

**Why:** this closes a real gap between the reference implementation and the
already-published PAC-ID-Attributes spec change (`ApiniLabs/PAC-Attributes` commit
`699e26e`, "iri instead of pac-id"), which says the id only has to be an IRI,
"preferably" a PAC-ID. Two concrete bugs were found while implementing this:

- `PAC_CAT._split_segments_by_category` and `_resolve_identifier_for_notation`
  (`pac_cat/pac_cat.py`) both did `segment.value[0] == '-'`, which raises an unhandled
  `IndexError` on an empty segment (e.g. from a repeated `/` - a single trailing `/`
  no longer produces an empty segment at all, see the 2026-07-29 revision above)
  instead of the clean,
  catchable `LabFREED_ValidationError` the "empty id segments" decision above assumes.
  Fixed by switching to `segment.value.startswith('-')`, which handles an empty string
  correctly (`''.startswith('-')` is simply `False`) without changing behavior for any
  non-empty segment.
- Routing a plain string through `PAC_ID.from_url(subject_id).to_url()` before sending
  it is actively harmful for a non-PAC-ID IRI: confirmed empirically that
  `PAC_ID.from_url("https://example.com/thing?x=1", suppress_validation_errors=True).to_url()`
  returns `"HTTPS://PAC.example.com/thing?x=1"` - the serializer unconditionally injects
  a `PAC.` issuer prefix and uppercases the scheme, silently corrupting any id that
  isn't already in that exact canonical form. Sending that corrupted id to the server
  instead of the real one is a data-integrity bug, not just a cosmetic mismatch.

**Alternatives considered / why not:**

- Keep parsing every `subject_id` string via `PAC_ID.from_url(..., suppress_validation_errors=True)`
  and use `.to_url()` on both sides for the response-identity comparison - rejected
  because of the corruption issue above, and because it's unnecessary: the server
  already echoes the `subject_id` it received back verbatim as the response `id`
  (`AttributeServerRequestHandler._get_attributes_for_pac_id` passes `pac_url` through
  unmodified), so a plain string comparison on both sides is both simpler and more
  faithful than reconstructing and re-canonicalizing a `PAC_ID` object neither side
  actually needs.
- Attempt a "round-trip check" (parse, reserialize, only trust the canonical form if it
  matches the original) - rejected as unnecessary complexity once the string-passthrough
  approach above sidesteps the corruption risk entirely.

**Impact:** a real PAC-ID passed as a `PAC_ID` object is still normalized as before
(case, extension formatting); a real PAC-ID passed as a `str` is no longer
canonicalized before being sent - this is intentional and matches how the server treats
it already (verbatim passthrough), not a regression, but worth knowing if some other
caller relied on the client silently uppercasing/reformatting a lowercase PAC-ID string.

*Investigated 2026-07-28, alongside implementing the IRI migration on branch
`iri-instead-of-pac-id`.*

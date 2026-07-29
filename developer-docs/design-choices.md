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
`Dict_DataSource.attributes()`, and `_BaseExcelAttributeDataSource.attributes()` fixed
the same way in Phase 2 of [[project_labfreed_pac_attributes_improvement_plan]]) needs
to account for the canonical form no longer matching a raw, as-stored key that still
carries the stripped slash - fixed by falling back to a raw-string lookup when the
canonical-key lookup misses. The fallback logic itself is duplicated between the two
data sources - see TODO.md, "Pull the shared... lookup out of the data sources".

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

---

## `do_forward_lookup` serializes as a lowercase string, not a Python bool

**Decision:** `AttributeRequestData.request_params()` (`api_data_models/request.py`)
sends `do_forward_lookup` as `str(self.do_forward_lookup).lower()` (`'true'`/`'false'`)
rather than the raw Python `bool`.

**Why:** `request_params()`'s output goes straight into a dict that `requests` turns
into an HTTP query string; a raw Python `bool` serializes as `attr_fwd_lkp=True` or
`attr_fwd_lkp=False` (capitalized, Python `repr` style), but the PAC-ID-Attributes spec
defines this as a string parameter and expects the conventional lowercase
`'true'`/`'false'`. This only worked before because the bundled reference server
happens to lowercase the incoming value before comparing it - a real third-party server
implemented strictly to spec could reject or misread the capitalized form.

**Alternatives considered / why not:**

- Leave it as a Python `bool` and rely on every server implementation lowercasing before
  comparing - rejected as fragile: it depends on undocumented server-side leniency that
  only this repo's own bundled server happens to provide.

**Impact:** none for callers going through `AttributeClient` - only the wire
representation changes, not any public API shape or type.

*Investigated 2026-07-29, while reviewing the IRI migration for other core bugs in the
same area.*

---

## Each Excel data source instance gets its own `TTLCache`

**Decision:** `_BaseExcelAttributeDataSource` (`pythonic/excel_attribute_data_source.py`)
now creates its own `TTLCache(maxsize=128, ttl=cache_duration_seconds)` per instance in
`__init__`, and `LocalExcelAttributeDataSource._read_rows_and_last_changed` uses
`@cachedmethod(lambda self: self._cache)` instead of a plain `@cached(_cache)` bound to
one module-level cache object.

**Why:** the previous code had a single `_cache = TTLCache(...)` shared by every
instance, and each `__init__` mutated that same object's `.ttl` to its own
`cache_duration_seconds`. Since `.ttl` is one scalar property of the whole cache, the
*last-constructed* instance's TTL silently applied to every other instance too - two
data sources configured with different cache lifetimes (e.g. one long-lived static
sheet, one short-lived frequently-changing one) would both end up using whichever TTL
was set most recently. Confirmed empirically: constructing a long-TTL instance, priming
its cache, then constructing a second short-TTL instance caused the first instance's
next read to still be a cache hit only because of decorator-level per-instance key
separation, not because its own TTL was respected - proving the *setting* was shared
even though cache *entries* happened to already be keyed per-instance via `self`.

**Alternatives considered / why not:**

- Keep one shared `TTLCache` but namespace keys by `(self, ...)` and track each
  instance's TTL separately outside the cache - rejected as needless complexity; a
  `TTLCache` already exists as a per-instance construct in `cachetools`, no need to
  simulate one on top of a shared object.

**Impact:** none observable for a single-instance-per-process usage pattern (the common
case); fixes real cross-instance interference for anyone constructing multiple data
sources with different `cache_duration_seconds` in the same process. See TODO.md,
"Pull the shared... lookup out of the data sources" for a related, still-open
duplication between this data source and `Dict_DataSource`.

*Investigated 2026-07-29, as Phase 3 item 2 of
[[project_labfreed_pac_attributes_improvement_plan]].*

---

## Two typo fixes in `well_knonw_attribute_keys` kept as deprecated shims, not silent renames

**Decision:** `labfreed/pac_attributes/well_knonw_attribute_keys.py` (the module name
itself has a typo - missing the "n" in "known") is now a thin shim: the real content
moved to `labfreed/pac_attributes/well_known_attribute_keys.py`, and the old module
re-exports from the new one plus emits a `DeprecationWarning` on import. Within that
module, `PhysoChemicalProperties` (also a typo - missing "ic") was renamed to
`PhysicoChemicalProperties` in the new module; the old module keeps
`PhysoChemicalProperties = PhysicoChemicalProperties` as a plain alias (no separate
warning - importing the old module already warns once).

**Why:** both are confirmed imported directly by `labfreed-webtools` (not purely
internal), so a straight rename would break an external consumer with no warning.
Per this package's `versioning` skill, a public rename gets a deprecation window, not
an instant break, while the package is still pre-1.0.

**Alternatives considered / why not:**

- Wrap the re-exported symbols with the `deprecated` package's `@deprecated` decorator
  instead of a module-level `warnings.warn` - rejected after confirming empirically that
  `@deprecated` on an `Enum` class does not fire when accessing a member
  (`SomeEnum.MEMBER`), only on constructing an instance via `__call__`/`__new__`, which
  enum member access never does. A module-level `warnings.warn(DeprecationWarning)` at
  import time is the only one of the two that actually fires for this usage pattern.
- Rename `MELTINGPOINT`'s *value* (`"meltinggpoint"` -> `"meltingpoint"`) at the same
  time, folded into this same decision rather than a separate one: this is a wire-format
  string change, not just an import path, but `MELTINGPOINT` has zero confirmed usages
  in `labfreed-webtools` and the whole enum is still an explicit `.../dummy/...`
  placeholder namespace (not yet a real spec-blessed key) - so unlike the class/module
  renames, there's no deprecation window that would even mean anything here; fixed
  directly instead. Tagged `BREAKING:` in `CHANGELOG.md` per the `versioning` skill's
  "ambiguous, decide deliberately" guidance, since it's a value change even though the
  practical blast radius is zero.

**Impact:** `labfreed-webtools/instrument_demo/bp_instrument_demo.py` and
`pac_issuer_demo/carlroth/attribute_datasources.py` still import the old module/class
names today and keep working unchanged via the shim; updating them to the new names is
tracked as Phase 3 item 8 of [[project_labfreed_pac_attributes_improvement_plan]].

*Investigated 2026-07-29, as Phase 3 items 3 and 5 of
[[project_labfreed_pac_attributes_improvement_plan]].*

---

## Resolver config's expression evaluation split out of the data model; `eval()` replaced with a direct token evaluator

**Decision:** `ResolverConfig`/`ResolverConfigBlock`/`ResolverConfigEntry`
(`labfreed/pac_id_resolver/resolver_config.py`) are now pure data models - field shapes
and structural validators only (`service_name`/`application_intents`/`service_type`
char/length rules, `applicable_if` defaulting). Everything behavioral - tokenizing
`applicable_if`, the bracket-key convenience substitution, jsonpath lookups, url
templating, and the `evaluate_pac_id` walk itself - moved to a new
`resolver_config_evaluator.py`, behind `ResolverConfigEvaluator(config).evaluate(pac)`.
`ResolverConfig.evaluate_pac_id()` is now a one-line delegating shim using a lazy import,
the same trick `PAC_ID.from_url()`/`to_url()` already use to avoid a circular import back
into `resolver_config.py`.

Folded into the same change: `_evaluate_applicable_if` used to reassemble the token
stream into a Python source string and call `eval()` on it - matched PAC-ID content
reached that string via unescaped f-string interpolation
(`f'"{res[0].upper()}"'`). Replaced with `_TokenEvaluator`, a small recursive-descent
walker over the same tokens that compares real Python values directly
(`operator.eq`/`lt`/etc.) and never builds or executes code.

**Why:**

- *Separation:* the model class had three unrelated jobs at once (data shape,
  expression grammar, execution), so a bug in the expression evaluator lived inside
  what's nominally a Pydantic schema, and testing the logic meant reaching into private
  methods on the model.
- *`eval()` removal:* a security review found `res[0].upper()` wrapped in an f-string
  was the only thing between attacker-controlled PAC-ID content and `eval()` - since
  anyone can mint a PAC-ID, this is untrusted input by design. Confirmed exploitable for
  an unhandled crash (a stray `"`/`(` in a matched field, or a non-string jsonpath match
  raising `AttributeError` on `.upper()`) and for structural injection (chained
  comparisons splicing extra literal syntax into the evaluated expression). Also
  confirmed `eval(expr, {}, {})` is not a sandbox regardless: Python auto-populates
  `__builtins__` into a bare `{}` globals dict, and even with `__builtins__` explicitly
  stripped, `().__class__.__bases__[0].__subclasses__()` alone still reaches ~170 live
  classes via the object graph.

**Alternatives considered / why not:**

- Keep `eval()` but escape the interpolated value properly (`json.dumps()`/`repr()`) -
  rejected: still a code-generation-from-untrusted-input design, and `eval()` isn't
  sandboxable in CPython regardless of escaping (see the subclass-graph proof above).
- `simpleeval` or another AST-whitelisting library - rejected in favor of a hand-rolled
  evaluator: the grammar here is tiny and already fully tokenized (AND/OR/NOT + 6
  comparison operators), so a ~90-line direct walker is less code and one fewer
  dependency than integrating a general-purpose safe-eval library correctly.

**Impact:** three more bugs surfaced by tests written against this area and fixed in the
same pass:

- Literal `True`/`False` conditions: the old eval-string builder quoted *any* bare-word
  literal (including the text `"False"`) into a non-empty, therefore truthy, string - so
  `applicable_if: "false"` could never actually evaluate falsy. `_TokenEvaluator` treats
  bare `TRUE`/`FALSE` as real Python booleans instead.
- Quoted string literals (e.g. `$.identifier[1].value == 'THOMAS'`) previously crashed
  the tokenizer with an unhandled `SyntaxError` on the quote character (reported
  upstream against github.com/ApiniLabs/PAC-ID-Resolver) - added a `STRING` token type
  so single- or double-quoted literals (spaces allowed) are valid syntax, compared as
  inert data.
- A malformed `applicable_if` (bad syntax, bad jsonpath) no longer crashes resolution of
  the whole PAC-ID - `ResolverConfigEvaluator.evaluate()` now catches
  `SyntaxError`/`JSONPathError` per block and treats that block as not-applicable, the
  same "stable against errors in the resolver config" contract invalid entries already
  had.
- `_apply_convenience_substitutions`'s bracket-key shorthand only rewrote
  double-quoted keys (`["key"]`); single-quoted (`['key']`) silently matched nothing.
  Confirmed this left real blocks permanently dead in two real-world configs used by
  `labfreed-webtools` (a `-MD`/`-MC` category gate, a macro-based service entry) - fixed
  by accepting either quote style.

Existing call sites (`resolver.py`, `labfreed-webtools/resolver_tester/bp_resolver_tester.py`)
are unaffected since `evaluate_pac_id`'s signature and behavior are unchanged; only the
private test hooks in `tests/test_resolver/test_resolver_config_v2.py` needed updating to
instantiate `ResolverConfigEvaluator` directly instead of calling private methods on
`ResolverConfig`.

*Investigated 2026-07-29.*

---

## Service-availability network checks split out of `Service`/`ServiceGroup`, with no shim

**Decision:** `Service.check_service_status()` and `ServiceGroup.update_states()` - along with
the free-floating `_has_internet_connection()` - are removed entirely from
`labfreed/pac_id_resolver/services.py`, not turned into delegating shims. The same logic now
lives in a new `service_availability.py` as plain module-level functions,
`check_service(service, session=None)` and `check_service_group(group, session=None)`, which
every former caller (`resolver.py`, `examples/examples.py`, `tests/test_sanity_check.py`,
`labfreed-webtools/resolver_tester/bp_resolver_tester.py`) now imports and calls directly instead
of calling a method on the model.

Folded into the same change: `check_service_group` no longer raises `ConnectionError` when
`_has_internet_connection()` fails. It now sets every service's `status` to the already-existing
`ServiceStatus.UNKNOWN` and returns normally.

**Why:** this is the same data-model-vs-logic coupling already fixed for
[`resolver_config.py`](#resolver-configs-expression-evaluation-split-out-of-the-data-model-eval-replaced-with-a-direct-token-evaluator) -
`status` is a plain field, but deciding its value required real HTTP I/O living inside the model
class. Unlike that fix, this one has no delegating shim at all: `ResolverConfig.evaluate_pac_id()`
was kept as a one-liner because evaluating itself against a PAC-ID is the model's own intrinsic
behavior; checking whether a URL is currently reachable over the network is not an intrinsic
property of "a service" as data, it's an operation performed on it by something external - so the
data model shouldn't expose a method for it at all, not even a thin one.

The raise-to-degrade change fixes a real bug: `ConnectionError` failing loudly meant a missing
connectivity check could abort `PAC_ID_Resolver.resolve()` (default args) even though PAC-ID
resolution itself had already succeeded - confirmed this is exactly what made
`tests/test_sanity_check.py::test_resolver` fail in a sandboxed/offline environment.
`ServiceStatus` already had an `UNKNOWN` value for exactly this situation; nothing previously set
it that way.

**Alternatives considered / why not:**

- A `ServiceAvailabilityChecker` class mirroring `ResolverConfigEvaluator`'s
  construct-then-call shape, for API consistency with the sibling module - rejected: that shape
  exists there to hold `self._config` across several private helper methods with exactly one call
  site (the shim). This logic is fully stateless and, without a shim, now has four real external
  callers across two repos - plain functions avoid pointless per-call-site instantiation ceremony.
- Keep the shim methods on `Service`/`ServiceGroup` (the same lazy-import pattern as
  `evaluate_pac_id`) - considered first, rejected on reflection: unlike evaluating a resolver
  config against a PAC-ID, "check my own network reachability" isn't something a data model
  should know how to do about itself, even via a one-line delegate.

**Impact:** every caller of the old `.update_states()`/`.check_service_status()` methods had to
change to call `check_service_group()`/`check_service()` instead - four call sites across
`LabFREED` and `labfreed-webtools`, all updated in the same change (no deprecation shim, since
this package is pre-1.0 and both are internal-only entry points, never part of a documented public
API). `ServiceGroup.print()`/`__str__` and the `resolver_tester_main.jinja.html` template that
branches on `s.status.name` are both unaffected - they only ever read `.status` after the fact, and
`ServiceStatus.UNKNOWN` was already a value they knew how to render.

Also surfaced, left out of scope: `labfreed/labfreed_extended/app/app_infrastructure.py` has its
own near-duplicate of this exact logic (`update_user_handover_states` plus a second, inconsistent
`_has_internet_connection` using `requests.head` instead of `requests.get`), confirmed dead code -
see [`TODO.md`](TODO.md#app_infrastructurepy-has-a-dead-second-copy-of-the-service-availability-logic).
Left alone since it's entirely inside the `pac_issuer_lib`/issuer-app area deferred to its own
branch.

*Investigated 2026-07-29.*

---

## `PhysicoChemicalProperties`' remaining dummy values replaced with real qudt.org URIs; new chemical-identity/spec/document keys split into their own enums

**Decision:** `well_known_attribute_keys.py` had three enum members still on the
`.../dummy/...` placeholder namespace (`BOILINGPOINT`, `MELTINGPOINT`, `DENSITY`).
These were replaced in place with the real `https://qudt.org/vocab/quantitykind/...`
URIs, matching what a real Apini attribute server returns for a Carl Roth solvent
(captured via `labfreed-webtools/scripts/test_apini_attribute_api.py`). `MOLARMASS` and
`FLASHPOINT` were added to the same enum (also `qudt.org` quantitykind URIs, same
response). The remaining new keys from that response - CAS number, EC number, empirical
formula, assay, water content, datasheet, safety data sheet - were **not** folded into
`PhysicoChemicalProperties`; they went into three new enums instead:
`ChemicalIdentifiers` (CAS_NUMBER, EC_NUMBER, EMPIRICAL_FORMULA),
`GuaranteeAnalysisProperties` (ASSAY, WATER_CONTENT), and `DocumentKeys` (DATASHEET,
SAFETY_DATA_SHEET). `POLARITY` was left untouched on its dummy value - the sample
response had no equivalent attribute to source a real URI from.

**Why:** an identifier (CAS/EC number, empirical formula) isn't a physicochemical
*property* in the sense the existing enum's other members are (boiling point, density,
etc.) - a CAS number doesn't measure anything about the substance, it names it.
Similarly, assay/water-content are QC/specification results (they came from the
response's "Guarantee Analysis" attribute group), not intrinsic physical properties,
and datasheet/SDS are documents, not data. Splitting by what the key actually
*represents* keeps `PhysicoChemicalProperties` a coherent "measurable property" bucket
rather than a catch-all for every attribute key ever seen.

**Alternatives considered / why not:**

- Add the `qudt.org` values as new, separate enum members alongside the existing dummy
  ones instead of replacing them in place - rejected the same way the prior
  `MELTINGPOINT` typo fix was: this enum is still an unreleased placeholder namespace
  with zero confirmed real-world usage (see the "Two typo fixes" entry above), so there
  was no deprecation window worth preserving, and keeping both would leave two keys per
  concept with no way for a caller to know which one a given server actually uses.
- Dump all twelve new/changed keys into a single new enum instead of three - rejected
  because it would mix identifiers, QC results, and documents under one name, losing
  exactly the grouping signal `MetaAttributeKeys` vs. `PhysicoChemicalProperties`
  already established as this file's own convention.

**Impact:** tagged `BREAKING:` in `CHANGELOG.md` per the `versioning` skill's "value
change to a serialized key" rule, even though - as with the earlier `MELTINGPOINT` fix -
the practical blast radius is zero (no confirmed caller reads `BOILINGPOINT`,
`MELTINGPOINT`, or `DENSITY` today). `POLARITY` staying on a dummy value is a known gap,
not an oversight - fill it in once a real server response with a polarity attribute is
seen.

*Investigated 2026-07-29, prompted by a real Apini attribute server response for a Carl
Roth DMSO solvent.*

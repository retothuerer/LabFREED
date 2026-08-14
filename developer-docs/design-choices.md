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
- Quoted string literals (e.g. `$.pac.identifier[1].value == 'THOMAS'`) previously crashed
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
`MELTINGPOINT`, or `DENSITY` today).

*Investigated 2026-07-29, prompted by a real Apini attribute server response for a Carl
Roth DMSO solvent.*

**Update 2026-08-03:** `POLARITY` deleted outright rather than left on its dummy value,
per the user's own call while auditing the package ahead of the 1.0.0 release - same
reasoning as the `NAME` alias deletion elsewhere in this same cleanup pass: zero
confirmed real-world usage, still on an unreleased placeholder namespace, so there's no
deprecation window that would mean anything here. Re-add it (with a real URI) once a
real attribute source that actually populates a polarity value shows up.

---

## PAC-ID-Attributes response parsing permanently tolerates the pre-migration wire shape (`pac_id` field, JSON-LD `@context` object)

**Decision:** `AttributesOfItem` (`api_data_models/response.py`) gained a
`model_validator(mode="before")` (`_accept_legacy_pac_id_field`) that falls back to
reading `pac_id` when `id` is absent - moved up from the deprecated `AttributesOfPACID`
subclass so it applies to the base class that `AttributeResponsePayload.data` actually
parses, not just a subclass nothing in the response-parsing path uses.
`AttributeResponsePayload.context` gained a `field_validator(mode="before")`
(`_accept_legacy_jsonld_context_object`) that unwraps the pre-"minimization" JSON-LD
object shape (`{"@import": "<url>"}`, see the "minimized import of `@context`" commit
`5424d8b`) back to a plain string; a bare string already passes through unchanged. Both
are input-only leniency - the model still always parses to `id: str` / `context: str`,
and output/serialization shape is unaffected.

**Why:** `LabFREED_BaseModel` sets `model_config = ConfigDict(extra="forbid")`, so a
server still emitting the pre-migration wire shape doesn't get ignored - it hard-fails
client-side parsing as `AttributeServerError` ("response is not adhering to the PAC
Attributes specifications"), even though the actual defect is version skew, not a
genuine spec violation by that server. Confirmed empirically against the real,
externally-hosted Apini Cloud Function attribute server
(`europe-west6-apini-cloud.cloudfunctions.net`, used by
`labfreed-webtools/instrument_demo/bp_instrument_demo.py`): it still emits the
pre-migration shape today, reproducing exactly 3 pydantic validation errors
(`extra_forbidden` on `pac_id`, `missing` on `id`, `string_type` on `@context`). That
server isn't part of this repo and can't be fixed here.

**Alternatives considered / why not:**

- Treat this as a temporary shim tied to Apini's migration status, with a `TODO.md`
  entry to remove it once that server updates - rejected. The repo owner explicitly
  chose to keep this permanently ("I'm fine if this stays forever") rather than track it
  as pending removal, since there's no reliable signal for *if or when* a third-party
  service will ever migrate - a "remove once X updates" TODO would sit forever with no
  way to know it's actionable.
- Reject old-format responses outright and require the server operator to fix it (the
  existing error message's own "contact the server admin" framing) - rejected as
  impractical: this external service is the demo webapp's only real attribute source
  today, so a hard requirement to fix a third-party server first would just mean the
  demo never works against real data.

**Impact:** `AttributesOfPACID` (deprecated) no longer redeclares the rename validator -
it now inherits the same behavior from `AttributesOfItem` unchanged. See
[[project_labfreed_iri_migration]] for the migration this shim is bridging around.

*Investigated 2026-07-29, while debugging `bp_instrument_demo.py`'s PAC-Ninja conversion
path returning no attributes.*

---

## Automatic, optional UNECE<->UCUM unit mapping via pint/ucumvert

**Decision:** `labfreed/well_known_keys/unece/ucum_bridge.py` is a new module that maps between
UCUM unit strings (used by `Quantity`, and therefore by T-REX's pythonic API and PAC-ID
Attributes) and UNECE Common Codes (mandated by T-REX's wire format for
`NumericSegment`/`ColumnHeader.type`), using `pint` + `ucumvert` for dimensional/scale-factor
matching instead of the previous string-equality hack. Both libraries are optional (a new `units`
extra in `pyproject.toml`) - the module soft-imports them, exposes `HAS_UCUM_SUPPORT`, and falls
back to the original fast exact-match/regex heuristics when absent, raising `UcumSupportError`
(naming the `pip install labfreed[units]` fix) only for the cases that genuinely need the library
and don't have it.

`quantity.py`'s `unece_unit_code_from_quantity` and both reverse-lookup call sites in
`pyTREX.py` try their existing dependency-free exact-match path first (still correct for plain SI
units - kg, m, s), and only fall through to `ucum_bridge` for compound/non-identical units
(`mol/L`, `kg/m3`, `Cel`, ...). `pac_attributes/api_data_models/response.py`'s
`NumericAttributeItemsElement._validate_unit` now shares `ucum_bridge.is_valid_ucum` instead of
its own separate regex (the blankspace/`^` hard-reject check stays inline, unchanged, ahead of
it).

**Why:** the old mapping (`unece_unit_code_from_quantity`) compared a Quantity's UCUM unit string
against UNECE's raw `name`/`symbol`/`commonCode` fields for byte-equality. That only works when
UNECE's display symbol happens to equal the UCUM string - true for `kg`/`m`/`s`, false for `Cel`
vs UNECE's `°C`, and false for essentially every compound unit (`mol/L`, `kg/m3`) since UNECE
symbols never use UCUM notation for those. There were also two independent, diverging
hand-written "is this valid UCUM" regexes (one in `quantity.py`'s coercion step, one in
`NumericAttributeItemsElement._validate_unit`).

Verified empirically (installed `pint`+`ucumvert` in a throwaway venv, ran real matching against
the actual bundled `UneceUnits.json`) rather than assumed: every active UNECE entry already
carries an unused `parsedSymbol` field (`"millimeter"`, `"degree_Celsius"`, `"1 / meter"`) that is
literal **pint** expression syntax - 1200/1211 parse cleanly with a stock `pint.UnitRegistry()`.
Using that field, dimensional/scale-factor matching against an arbitrary UCUM string (parsed via
`ucumvert`, the only Python package found that converts UCUM to pint) resolves correctly with
zero hand-curated table: `kg/m3` matches `KMQ`/`GL`/`F23` (all three really are the same physical
quantity - UCUM has no canonical form, so multiple hits is correct, not a bug), `mmol/L` matches
`M33`, etc. Building the quantity via `ureg.parse_expression(...)`/`ureg.from_ucum(...)` directly
(both already return a `Quantity`) rather than re-multiplying by a bare scalar was required to
avoid `pint`'s `OffsetUnitCalculusError` on `degree_Celsius`/`degree_Fahrenheit` - confirmed by
isolating the exact failing call (`1 * <already-a-Quantity>`) in the same throwaway venv.
`ucumvert` only converts UCUM->pint (confirmed from its source/README: "currently only the
conversion direction from UCUM to pint is supported"), so the reverse direction (UNECE code ->
UCUM string) instead normalizes UNECE's own `symbol` field (superscript digits, `µ`->`u`,
`°C`->`Cel`, `·`->`.`) - already valid UCUM for 877/1511 active entries without any table at all;
the residual gap is almost entirely imperial/trade units (`oz/ft²`, `BtuIT/h`) that don't occur in
lab data, and is left for `ucum_for_unece_code` to raise `UcumSupportError` on, lazily, rather than
curated upfront.

`pint`/`ucumvert` were kept optional (not core dependencies like `pydantic`) specifically because
they're new to this codebase and less central/proven here - an optional extra with a
dependency-free fast path for the common case, degrading to a named, actionable error rather than
a crash for the rest, was judged the better tradeoff than either hand-curating ~2000 UNECE rows or
making the whole package depend on them.

**Alternatives considered / why not:**

- Hand-curate a UNECE-code -> UCUM lookup table covering all ~2159 codes - rejected: explicitly
  what this change was meant to avoid; the empirical finding that `parsedSymbol` already encodes
  everything needed for physical-equivalence matching made a full manual table unnecessary.
- Make `pint`/`ucumvert` hard dependencies - rejected: they're peripheral (only touch the
  UNECE<->UCUM boundary) and comparatively new/unproven in this codebase, unlike `pydantic`; an
  optional extra with graceful degradation keeps the core package unaffected if either library
  breaks or is abandoned.
- Guaranteeing every compound-unit round trip returns the *original* exact string - rejected:
  UCUM has no canonical form (`ucumvert`'s own docs note `m/s` and `m.s-1` are the same unit two
  ways), so a round trip through a T-REX UNECE code is only guaranteed to preserve the physical
  quantity, not the input string byte-for-byte. Made explicit via `best_unece_code_for_ucum`'s
  documented, deterministic tie-break (own-symbol match, then `LEVEL_1_NORMATIVE`, then lowest
  `commonCode`) rather than leaving the choice among equally-valid codes unspecified.

**Impact:** `quantity.py`'s `unece_unit_code_from_quantity`, both reverse-lookup sites in
`pyTREX.py`, and `NumericAttributeItemsElement._validate_unit` in `response.py` all changed
internally (none are public API - free to change without a deprecation shim, this package is
pre-1.0). The reverse-normalization gap in `ucum_for_unece_code` (~40% of UNECE symbols,
overwhelmingly imperial/trade units) is tracked in
[TODO.md](TODO.md#fill-in-ucum_for_unece_codes-normalization-gaps-as-theyre-actually-hit).

*Investigated 2026-07-29.*

---

## `Quantity` validates its unit is UCUM at construction time, with an explicit opt-out

**Decision:** `Quantity.transform_inputs` now rejects (`ValueError`) any non-empty `unit` that
`ucum_bridge.is_valid_ucum` doesn't accept - structural syntax only without the optional `units`
extra, a real symbol-level parse via `ucumvert`/`pint` with it. The constructor accepts a
`dont_enforce_ucum_units: bool = False` keyword that skips this check entirely; it's popped out of
the input dict in `transform_inputs` (the same pattern already used for `decimals`) rather than
stored as a model field, so it never becomes part of `Quantity`'s persisted state.

**Why:** previously `Quantity(unit=...)` accepted any string at all - `unece_unit_code_from_quantity`
and PAC-ID Attributes' own `NumericAttributeItemsElement._validate_unit` were the only places a bad
unit ever got caught, and only downstream, sometimes much later than construction. Since the
package is committing to UCUM as *the* unit representation in Python (see the previous entry),
`Quantity` itself - not just its consumers - should refuse to hold an invalid one. The escape hatch
exists because one caller *legitimately* needs to construct a `Quantity` from a unit that already
failed validation elsewhere without crashing: `pyAttributes.from_payload_attributes` reconstructs a
`Quantity` from a received `NumericAttributeItemsElement`, whose `_unit` was already checked by
`response.py` at WARNING level (non-fatal, by design - see ["Non-fatal, severity-tiered
validation"](#non-fatal-severity-tiered-validation-instead-of-plain-pydantic-errors)). Re-validating
strictly on the way back into a `Quantity` would turn that already-accepted WARNING into a hard
crash, which would contradict the whole point of treating it as non-fatal in the first place - so
that one call site passes `dont_enforce_ucum_units=True` explicitly, with a comment explaining why.

The other place a unit string reaches `Quantity` from outside the type system -
`pyAttributes._attribute_to_attribute_payload_type`'s heuristic detection of "number space word"
strings like `"100.0e5 g/L"` (via `Quantity.can_convert_to_quantity`) - deliberately does *not* use
the bypass. That regex only checks "a number followed by some word", not that the word is a valid
unit (e.g. it also matches `"5 boxes"`), so a `ValueError` there is now caught and the value falls
back to a plain `TextAttributeItemsElement` instead of propagating - restoring the same "guess, and
fall back to text if the guess doesn't hold up" behavior the heuristic always intended, just now
enforced by `Quantity` instead of silently accepting whatever word followed the number.

**Alternatives considered / why not:**

- Only validate in `NumericAttributeItemsElement`/`unece_unit_code_from_quantity` as before, leave
  `Quantity` itself permissive - rejected: this is exactly the gap that let invalid units survive
  construction and surface as confusing failures later, sometimes only at T-REX serialization time.
- A module-level flag (mirroring `HAS_UCUM_SUPPORT`) instead of a per-call keyword - rejected: the
  need to bypass is a property of one specific call site's data provenance (already-validated wire
  data), not a global policy; a keyword keeps the exception scoped to exactly the call that needs it.

**Impact:** constructing a `Quantity` with a non-UCUM unit now raises where it previously
succeeded silently - `BREAKING`, flagged in `CHANGELOG.md`. Two unit strings in this repo's own
examples/tests (`'hour'`) were never valid UCUM (`'h'` is) and were fixed as part of this change.

*Investigated 2026-07-29.*

---

## Ease of use is prioritized over textbook-clean separation of concerns; data types carry their own behavior

**Decision:** Core types across the package (`PAC_ID`, `PAC_CAT`, `Quantity`, `DataTable`,
`LabFREED_BaseModel` and its validation-message API, ...) hold parsing, serialization,
formatting, and validation directly as methods on the model itself, rather than routing
them through separate Factory/Validator/Serializer classes. Construction from external
representations goes through classmethods on the type (`PAC_ID.from_url`,
`Quantity.from_str_value`, `pyAttributes.from_payload_attributes`, ...), not dedicated
`*Factory` types - the only two `*Factory` classes in the repo
(`attribute_server_factory.py`, `app_factory.py`) live in `labfreed_extended`, not in any
core building block.

**Why:** the primary audience is someone writing a script against a PAC-ID/T-REX/etc. who
wants to `import PAC_ID`, call `.from_url()`, and be done - not someone assembling a
`PACIDFactory` + `PACIDValidator` + `PACIDSerializer` first. Keeping behavior on the type
it belongs to means one import and one object account for the whole interaction with a
concept, which matters more for a library whose main value is being easy to pick up than
for an internal service where testability-in-isolation and strict single-responsibility
would normally win out.

**Alternatives considered / why not:** none formally trialed as a rewrite - this documents
the standing, repo-wide convention (confirmed by grep: only 2 `Factory` classes total,
both outside core) rather than a single point-in-time investigation. The textbook
alternative - anemic data models plus dedicated factory/validator/serializer classes per
type - was implicitly rejected from the start in favor of the above; `url_parser.py`'s own
docstring makes the same call explicitly for the parsing side (see "`pac_id` depends on
`pac_cat`..." entry above - "we have given priority to convenient usage").

**Impact:** classes like `PAC_ID` and `Quantity` mix several responsibilities (parsing,
validation, formatting, sometimes normalization) in one class body, and can't be
unit-tested with one responsibility swapped out in isolation the way a narrower class
could. This is a standing, intentional tradeoff, not something to "clean up"
opportunistically - see the README's "Design Philosophy" section for the same tradeoff
stated for users of the package, not just contributors.

*Investigated 2026-07-30, while phrasing this tradeoff for the README's new "Design
Philosophy" section.*

---

## `PAC_ID.get_parent_pac_id()` covers issuer self-derivation too, not just `+<namespace>`-marked derivation

**Decision:** `PAC_ID.get_parent_pac_id()` treats a PAC-ID as having a parent in two
cases, not one: (1) it has a `+<namespace>` marker - parent is everything up to the
*last* marker (unchanged) - and (2), even without any marker, its identifier has more
than one id segment - parent is the identifier with its last segment dropped (e.g.
`.../-MD/BAL500/134`'s parent is `.../-MD/BAL500`), unless that would leave nothing but
a bare, field-less category key (`.../-MD/BAL500` itself has no parent, since dropping
`BAL500` leaves only `-MD`). Either way extensions are dropped, same as before. When
neither case applies, the method now returns `None` rather than `self` - "no marker"
no longer means "this is already the root," so there's no meaningful identity value
left to fall back to.

This logic previously lived only in `AttributeServerRequestHandler._get_derivation_parent_id`
(server.py), duplicating case (1) via a direct call to `get_parent_pac_id()` and
reimplementing case (2) inline. It has been moved onto `PAC_ID` itself and `server.py`
now just calls `get_parent_pac_id()` and converts to a url, per the "data types carry
their own behavior" convention (see "Ease of use is prioritized over textbook-clean
separation of concerns" above) - `get_parent_pac_id()` is the one full definition of
"parent" for a `PAC_ID`, not something server.py should partially reimplement.

**Why:** the PAC-ID spec's "Issuing derived PAC-ID"s section describes derivation as one
concept with two forms - an issuer forming a more specific PAC-ID by appending id
segments to its own PAC-ID (product -> batch -> container, no marker), and a third party
doing the same to someone else's PAC-ID (marker required, purely to preserve
attribution). The `+<namespace>` marker is a *third-party attribution* mechanism, not
the definition of "derived" - conflating "has a marker" with "has a parent" would
silently miss every issuer-derived PAC-ID, which given the spec's own worked examples is
probably the more common case in practice. `get_parent_pac_id()` originally implemented
only the marker case (added same day, never released - see CHANGELOG.md), which is what
surfaced the gap.

**Alternatives considered / why not:**

- Keep the marker as the sole signal (the original implementation) - rejected once the
  `BAL500/134` example was raised: it directly contradicts the spec section's own
  primary example, which never uses a marker at all.
- Recursively strip every trailing segment back to the root, rather than one segment at
  a time - rejected: without a marker there's no way to know how many segments the
  issuer added in one derivation "step" (unlike the marker case, where the boundary is
  explicit), so only the *immediate* one-segment-back parent is well-defined; guessing
  further back risks reporting an intermediate stage that was never actually issued as
  its own PAC-ID.
- Drop the last segment unconditionally, even down to a bare category key - rejected: a
  bare key like `-MD` with no fields isn't an entity anything could plausibly hold
  attributes for, so it's excluded rather than treated as a real parent.
- Keep the duplicate logic in server.py rather than relocating it - rejected: it's
  generic `PAC_ID` behavior with no dependency on anything attribute-server-specific,
  and leaving it duplicated risks the two copies drifting apart.
- `is_derived_from`'s ancestor walk still only follows the marker-based chain (its loop
  stops as soon as `has_derivation_segments()` is false) - deliberately left alone here;
  extending it to walk no-marker ancestry too is a further behavior change, not yet
  scoped.

**Impact:** `do_derivation_lookup` (default `True`, in the attribute server) now
triggers an extra attribute lookup for almost any multi-segment PAC-ID subject, not just
marker-derived ones - a wider set of PAC-IDs than before will get a `+1` request against
the configured data sources. Mitigated by the existing `do_derivation_lookup=False`
opt-out, same as `do_forward_lookup`. More broadly, any other caller of
`get_parent_pac_id()` must now handle a `None` return.

*Investigated 2026-07-30, following up on the PAC-ID-Attributes parent-lookup feature
added the same day; relocated from server.py into `PAC_ID` the same day after a test
review caught `get_parent_pac_id()` not yet covering the no-marker case.*

---

## Python floor pinned to exactly 3.14, not widened to the real code-imposed minimum

**Decision:** `pyproject.toml`'s `requires-python` stays `>=3.14`, a single minor version
with no attempt to widen it - even though the only actual *code* constraint
(`itertools.batched` in `labfreed/trex/table_segment.py`, added in Python 3.12) would
allow going as low as 3.12.

**Why:** the package has essentially one active user today, so there's no existing
installed base on an older interpreter to keep working - the usual reason to support a
wide version matrix doesn't apply yet. `developer-docs/README.md` previously carried a
stale warning that 3.14 itself was the *broken* version (pydantic failing to evaluate
`float | int`-style forward refs under 3.14's deferred-annotation-evaluation change) -
re-checked empirically against the current pydantic (2.13.4): the full test suite passes
cleanly on 3.14.6 (348 passed, 9 skipped, 0 failed), so that caveat no longer holds and
isn't a reason to avoid 3.14 either.

**Alternatives considered / why not:**

- Widen to `>=3.12` (the real floor `itertools.batched` imposes) - rejected for now: only
  3.14 was actually run in the environment this decision was made in; 3.12/3.13 were never
  verified, and claiming support for versions nobody tested would be worse than being
  explicit about the one version actually confirmed working.
- Keep `developer-docs/README.md`'s old "3.11-3.13, 3.14 broken" guidance and treat
  `pyproject.toml`'s `>=3.14` as the bug to revert - rejected once tests were actually run:
  the dev-docs note was the stale side, not the packaging metadata. 3.11 wasn't even a
  real option regardless, since `itertools.batched` doesn't exist there.

**Impact:** CI (`run-tests.yml`, `pypi-publish.yml`) moved from testing on 3.11 (a version
the package can't even import on) to 3.14, matching `requires-python`. Revisit and widen
the floor once there's real external adoption and/or someone actually verifies 3.12/3.13
pass too.

*Investigated 2026-07-30, prompted by a question about why `requires-python` looked
inverted relative to `developer-docs/README.md`'s (stale) setup note.*

---

## Well-known action handler: `action-generic` params travel as plain query params, not through the CIT template

**Decision:** the new `labfreed_experimental.actions` package (a fixed set of
well-known actions - `update-location`, `update-amount`, `container-is-empty` - with a
Flask HTTP layer dispatching to a pluggable `ActionBackend`) has its resolved
action URL take *only* the CIT's usual PAC-ID-derived substitutions. Anything the
action itself needs beyond that (the new location's PAC-ID, the UCUM quantity) is
appended by the caller as ordinary query parameters on top of the resolved URL, outside
the CIT templating mechanism entirely - e.g. a resolved `.../actions/update_location`
gets called as `.../actions/update_location?pac_id=...&location=...`.

**Why:** checked both the published spec and the reference implementation for a
convention here, and neither has one. `ServiceType.ACTION_GENERIC` /
`"action-generic"` (`pac_id_resolver/resolver_config_common.py`) is real and already
wired up end-to-end - `ResolverConfigEntry`/`ResolverConfig` accept it,
`ResolverConfigEvaluator._eval_url_template` resolves its `template_url`, and
`Labfreed_App_Infrastructure.process_pac()` already surfaces matching services as
`pac_info.actions` - but it is **not** in the published PAC-ID-Resolver spec (confirmed
via a fetch of the spec repo: the published spec documents only `userhandover-generic`
and `attributes-generic`), so it's an unpublished, implementation-only extension.
More importantly, `_eval_url_template`'s placeholder substitution
(`{$.jsonpath}`, read via `ResolverConfigEvaluator._evaluate_jsonpath`) only ever pulls
values out of the PAC-ID being resolved (`pac.to_dict()`) - there is no mechanism, in
the spec or the code, for a caller to feed additional runtime values (a second PAC-ID,
a quantity that isn't part of the subject PAC-ID at all) into that substitution. Same
finding holds for the older, deprecated `CIT_v1._find_pattern_in_pac` mechanism.

**Alternatives considered / why not:**

- Encode the location PAC-ID / quantity as a `{placeholder}` resolved from some
  invented pseudo-JSONPath - rejected: would require inventing syntax with no basis in
  either the spec or `resolver_config_evaluator.py`, and the CIT's whole templating
  contract is "derived from the PAC-ID being resolved," not "arbitrary caller-supplied
  values." Overloading it would be surprising to any other CIT consumer.
- Wait for the spec/reference implementation to define an official convention before
  building this - rejected: `action-generic` itself is already unpublished/ahead of
  spec, and there is no indication one is imminent. Plain query params on top of the
  resolved URL is the smallest thing that works today, and doesn't block on someone
  else's timeline.

**Impact:** any `action-generic` consumer of this package - not just
`SignalsActionBackend` - inherits the same contract: resolve the action's base URL
through the CIT as usual, then append whatever extra parameters the specific action
needs as a query string. If `action-generic`/parameter-passing is ever formalized in
the published spec, this package's Flask layer (`flask_layer.py`) is the one place
that would need to change to match it.

*Investigated 2026-07-30, while designing `labfreed_experimental.actions` for
labfreed-webtools' `instrument_demo` (Signals Notebook inventory sync).*

---

## Attribute-key enums migrated from `Enum` to `StrEnum`

**Decision:** the ten well-known-attribute-key enums in
`labfreed/pac_attributes/well_known_attribute_keys.py` (`MetaAttributeKeys`,
`IdentifierKeys`, `PhysicoChemicalProperties`, `ChemicalAppearanceProperties`,
`RegulatorySafetyKeys`, `StorageHandlingShippingKeys`, `BiologyAssayKeys`,
`CommercePackagingKeys`, `DocumentKeys`, `EventAttributeKeys`) now derive from
`StrEnum` instead of plain `Enum`, matching the convention `CommonQuantityUnit`
(`labfreed/utilities/quantity.py`) already used.

**Why:** prompted by the user noticing the inconsistency directly - `CommonQuantityUnit`
already derives from `StrEnum` so its members compare, hash, and format as plain
strings, while the attribute-key enums didn't, forcing `.value` at every call site to
satisfy `pyAttribute.key: str` (confirmed ~30 such call sites across `examples/*.py`
and `pac_info.py`). Verified empirically (throwaway `Enum` vs `StrEnum` classes in a
REPL) that this asymmetry has a real, *silent* failure mode, not just a boilerplate
cost: a plain-`Enum` member's `hash()`/`==` don't match the raw string it wraps, so
`dict.get(MetaAttributeKeys.IMAGE)` against a plain-string-keyed dict returns `None`
instead of raising - exactly the shape of bug `pac_info.py:164`'s
`self._all_attributes.get(MetaAttributeKeys.IMAGE.value)` would hit if the `.value`
were ever dropped by accident. Separately verified pydantic v2 already coerces a plain
`Enum` member into a `str` field by extracting `.value` automatically, so the `.value`
calls at `pyAttribute(key=...)` construction sites were already redundant there - the
real risk was confined to plain dict/set lookups and `==` comparisons outside pydantic.

**Alternatives considered / why not:**

- Leave `.value` as the required access pattern - rejected: pure boilerplate at every
  call site, and the dict-lookup/equality failure mode above is silent rather than
  loud - it doesn't raise, it just silently returns the wrong thing.
- Keep plain `Enum` for stricter type separation from arbitrary strings - rejected:
  nothing in this file needs that separation enforced at the type-system level; these
  are just constants for well-known IRIs, same role `CommonQuantityUnit` already fills
  as a `StrEnum`.

**Impact:** now-redundant `.value` calls stripped from `pyAttribute(key=...)`,
dict-literal keys, and `Term.create(...)` call sites in `examples/*.py` and
`pac_info.py`. Tagged `BREAKING:` in `CHANGELOG.md`'s pending `v1.0.0` entry per the
`versioning` skill's "ambiguous, decide deliberately" guidance: functionally backward
compatible for existing `.value` call sites, but `isinstance(key, str)` and `str(key)`
now behave differently than before. Other plain-`Enum` classes in the codebase were
surveyed for the same treatment; `ServiceType`, `WellKnownKeys`,
`GS1ApplicationIdentifier`, and `ServiceUUID`/`PAC_Characteristics` were converted too
(same day) once the user confirmed the blast radius of each was acceptable - see
[[developer-docs/TODO.md]] for the per-class detail, including one pre-existing,
unrelated latent bug (`cit_v1.py:190`) surfaced while checking `ServiceType`'s call
sites but deliberately left unfixed as out of scope.

*Investigated 2026-07-31, prompted by the user contrasting this file with
`CommonQuantityUnit`'s existing `StrEnum` usage.*

---

## `auto()`-backed enums (`ServiceStatus`, `ValidationMsgLevel`) also converted to `StrEnum`, with new explicit string values

**Decision:** following up on ["Attribute-key enums migrated from `Enum` to
`StrEnum`"](design-choices.md#attribute-key-enums-migrated-from-enum-to-strenum), the
two remaining plain-`Enum` classes that had been left alone as "not candidates"
because their members were `auto()`-generated ints - `ServiceStatus`
(`labfreed/pac_id_resolver/services.py`: `ACTIVE`/`INACTIVE`/`UNKNOWN`) and
`ValidationMsgLevel` (`labfreed/labfreed_infrastructure.py`:
`ERROR`/`WARNING`/`RECOMMENDATION`/`INFO`) - were converted too, at the user's request,
by giving them explicit lowercase string values (e.g. `ACTIVE = "active"`) and deriving
from `StrEnum`. `Webframework` (`attribute_server_factory.py`, already string-valued)
and `Direction` (`qr/generate_qr.py`, already `class Direction(str, Enum)`) were
converted/modernized to `StrEnum` in the same pass - both were pure base-class swaps
with no value change.

**Why:** the user's reasoning was "there's nothing that speaks against it, and it
reduces the `.value` error surface" - and for `Webframework`/`Direction` that's exactly
right, same mechanical swap as the first round. `ServiceStatus`/`ValidationMsgLevel`
are a materially different kind of change, though, and worth distinguishing:
their *values* change (int -> string), not just their base class - unlike every enum in
the first round, where the string value was untouched and only comparison/hashing
behavior changed. Checked empirically before doing this: neither enum had any
`.value`-reading call site anywhere in the codebase (both were only ever compared via
`==` or displayed via `.name`), and `ValidationMessage`/`Service` (the models that hold
these enums as fields) are never `model_dump()`/`model_dump_json()`'d in this codebase
today - `ValidationMessage` lives inside `LabFREED_BaseModel._validation_messages`, a
`PrivateAttr` excluded from the parent's serialization by default. So the practical
blast radius inside this repo is zero, but the *type* of change is still worth flagging
distinctly: an external consumer who serialized either model directly, or read
`.value` on either enum, would see a string where an int used to be.

**Alternatives considered / why not:**

- Leave `ServiceStatus`/`ValidationMsgLevel` on `auto()` ints since nothing in-repo
  reads `.value` - rejected: the user's ask was explicitly about consistency and
  closing off the `.value` error surface everywhere it plausibly could recur, not just
  where a live bug was already confirmed; also, an int enum with `auto()`-assigned
  values is itself a latent footgun for exactly this same "value that's not really the
  value you'd want serialized" class of issue.
- Give `ValidationMsgLevel` numeric string values (`"1"`/`"2"`/...) to stay closer to
  the old ints - rejected: the human-readable names (`"error"`, `"warning"`, ...)
  already exist as `.name`, and are far more useful as an actual `.value` than
  renumbered ints would ever have been.

**Impact:** no in-repo call sites needed updating (none read `.value` on either enum).
Tagged `BREAKING:` in `CHANGELOG.md`'s pending `v1.0.0` entry, called out separately
from the base-class-only conversions since this one changes actual serialized values,
not just comparison semantics.

*Investigated 2026-07-31, same session as the entry above, once the user asked to
extend the same treatment to the two enums that had been left out.*

---

## `card-components.jinja.html` macros converted from implicit-context to explicit-parameter style

**Decision:** the info-card macros in
`labfreed/labfreed_extended/pac_issuer_lib/templates/pac_info/card-components.jinja.html`
(`card_title`, `card_image`, `card_main`, `card_category_info`, `safety_pictograms`,
`qualification_state`) took no arguments and instead read a bare `pac_info` name
resolved from the ambient render context. They're now `card_title(pac_info)`,
`card_image(pac_info)`, etc., matching the explicit-parameter style
`base-components.jinja.html`'s macros already used. `card.jinja.html`'s `info_card`
macro (which calls all of these) was updated to pass `pac_info` through explicitly.

**Why:** this was a direct prerequisite for the upcoming CLP digital-label template
(Phase 4b of the PAC-ID Attributes improvement plan), which needs to reuse
`safety_pictograms()` and `card_info_block()` outside the existing card layout. That's
impossible while they silently depend on `pac_info` happening to be present in
whatever context they're rendered under - a template that isn't rendering a
`PacInfo`-shaped page at all has no such variable to depend on.

**Alternatives considered / why not:**

- Merge `card-components.jinja.html` into `base-components.jinja.html` into one macro
  module, per the originating plan's "consider merging the two files" suggestion -
  rejected: the two files serve genuinely different roles (`base-components` is
  generic PAC-attribute rendering reusable anywhere; `card-components` is specifically
  the info-card widget's layout). Merging would have widened this change's diff and
  its webtools-coordination surface (see Impact) for no functional benefit over just
  documenting the split, which the plan offered as an equally acceptable alternative.

**Impact:** no webtools call sites needed updating for this part - `card.jinja.html`
was the only importer of `card-components.jinja.html` within this repo, and it's
edited in the same change. See the next entry for the coordination that *was* needed
in `labfreed-webtools`, and for a related dead-code/bug finding in
`labfreed-webtools/pac_issuer_demo/acme_labs/` (out of scope, flagged in
[[developer-docs/TODO.md]]).

*Investigated 2026-07-31, Phase 4 item 8 of the PAC-ID Attributes improvement plan
(`plans/pac-id-attributes-implementation-is-distributed-pelican.md`), on branch
`cleanup-labfreed-library-for-release-1.0.0`.*

---

## `card.jinja.html` split to fix a double-render on every landing-page render

**Decision:** `card.jinja.html` used to both *define* the `info_card(pac_info)` macro
and *call* it at the template's top level (`{{ info_card(pac_info) }}`), so that
requesting the standalone card directly (`GET /info_card`, the HTMX-fetch route) would
render it. But `pac_info.jinja.html` also *imports* `card.jinja.html` (`with context`)
purely to call `card.info_card(pac_info)` explicitly as part of the full landing page -
and importing a template with `with context` in Jinja instantiates a fresh module by
running its top-level statements, which re-executes that same top-level
`{{ info_card(pac_info) }}` call as a side effect, every time. Verified empirically: a
property-access counter on `pac_info.display_name` (read once per `card_title()` call)
showed 4 accesses per landing-page render before this fix, 2 after - the final
rendered HTML was byte-identical in both cases, since the discarded import-side-effect
render's output is never concatenated into the page. So this was a pure
wasted-computation bug, not a duplicate-content one.

Fixed by splitting into two files, per the file's now-single job each: `card.jinja.html`
is macro-only (no top-level render call); a new `card_standalone.jinja.html` is the
thin wrapper (`{% import 'pac_info/card.jinja.html' as card with context %}` +
`{{ card.info_card(pac_info) }}`) for the one legitimate direct-render use case.

**Why:** the file was serving two jobs - "macro library" and "standalone page" - and
only one job should determine whether the top-level statement runs.

**Alternatives considered / why not:**

- Keep one file, but skip the top-level call when a "just importing" flag was set -
  rejected: needs a context flag threaded through every call site for no benefit over
  just splitting into two small files, one per job.

**Impact:** two call sites rendered the old combined file by template name and needed
updating to `card_standalone.jinja.html` - this repo's own
`app_factory.py`'s `/info_card` route (via `render_from_bp`), and
`labfreed-webtools/pac_info/bp_pac_info.py`'s `pac_card()` route (via Flask's
`render_template`) - both updated as part of this change.

While tracing every consumer of these template names to find those two call sites,
found that `labfreed-webtools/pac_issuer_demo/acme_labs/` ships its own full override
copies of `card.jinja.html`, `card-components.jinja.html`, and `pac_info.jinja.html`
(via `IssuerFlaskAppFactory`'s per-issuer custom-resources `ChoiceLoader`). Confirmed
this change doesn't break or improve anything there either way - acme_labs's own
override files fully shadow the package defaults for that blueprint regardless of what
the package does. Three separate pre-existing bugs found in acme_labs's own copies
along the way (its own independent instance of this same double-render bug, a dead
unused import, and a leaked debug string rendered into the live page) - not fixed here,
flagged in [[developer-docs/TODO.md]] instead, matching this plan's established
pattern of flagging out-of-scope pre-existing bugs rather than silently fixing them.

*Investigated 2026-07-31, Phase 4 item 8 of the PAC-ID Attributes improvement plan
(`plans/pac-id-attributes-implementation-is-distributed-pelican.md`), on branch
`cleanup-labfreed-library-for-release-1.0.0`.*

---

## CLP digital-label skeleton: no dedicated skeleton file, content-model decisions, and a `find_attributes()` helper

**Decision:** Phase 4b of the PAC-ID Attributes improvement plan asked for a generic
skeleton template for CLP's "digital label" (Regulation (EU) 2024/2865). Landed as:

- `labfreed/labfreed_extended/pac_issuer_lib/templates/digital_label/digital_label.jinja.html` -
  the content, built entirely from the existing `pac_info/base-components.jinja.html`
  and `pac_info/card-components.jinja.html` macros (no bespoke rendering of its own).
  Surfaces a "Hazard Information" block (pictograms, signal word, hazard statement,
  precautionary statement, UFI) immediately after the product-identity block, before
  falling through to the same services/attributes/attached-data sections
  `pac_info/pac_info.jinja.html` already renders.
- **No new skeleton file**, despite the plan's own suggested filename
  (`digital_label_skeleton.jinja.html`) - `pac_issuer_landing_page_skeleton.jinja.html`
  turned out to already be fully content-agnostic (just an HTMX loading shell with no
  reference to `pac_info` at all), so a near-duplicate file would have added nothing.
  An issuer adopting the digital label reuses that skeleton unchanged and overrides
  only `pac_issuer_landing_page.jinja.html` (their own copy, via the existing
  `IssuerFlaskAppFactory` custom-resources `ChoiceLoader` mechanism - same one
  `acme_labs` already uses) to `{% include "digital_label/digital_label.jinja.html" %}`
  instead of `{% include "pac_info/pac_info.jinja.html" %}`. No `app_factory.py`
  routing change was needed for this.
- A new `find_attributes(attribute_groups, keys)` helper
  (`lib/render_predicates.py`) looks up specific well-known-key attributes across all
  of a `PacInfo`'s groups, in caller-specified order, skipping any that aren't present -
  lets the template pull exactly the handful of fields CLP cares about into a
  highlighted block regardless of which group the data source put them in. Registered
  in `render_context_utils` (the same dict `is_url`/`is_reference`/etc. already flow
  through into `bp._jinja_env.globals` via `_build_jinja_env` - see the previous
  entry), alongside the `RegulatorySafetyKeys`/`DocumentKeys`/`IdentifierKeys`/
  `CommercePackagingKeys` enum classes themselves, so the template can reference e.g.
  `RegulatorySafetyKeys.GHS_SIGNAL_WORD` directly instead of a hand-copied URI string -
  single source of truth, no drift risk. Caveat: this only reaches templates rendered
  via `render_from_bp` (every route inside `pac_issuer_lib` itself). A consumer
  rendering via Flask's own `render_template` - e.g. `lib/attribute.py`'s
  `render_template_with_results`, used by `labfreed-webtools` - would need to pass
  `find_attributes`/the enum classes as explicit context kwargs, same as it already
  does for `is_url`/`is_image`/etc. Not needed for this pass since nothing wires the
  digital label template into that path yet.

**Why (content-model decisions, confirmed with the user rather than decided solo, per
the plan's explicit checkpoint):**

- **UFI** (Unique Formula Identifier, mandatory on the label for notified hazardous
  mixtures) - no well-known key existed. Added `RegulatorySafetyKeys.UFI =
  "https://www.wikidata.org/wiki/Q61745460"`. Sourced via web search (title-matched
  "Unique Formula Identifier" on Wikidata, same sourcing pattern as this class's other
  entries, e.g. `CLP_ANNEX_VI_INDEX_NO`) - not independently re-verified by fetching
  the Wikidata page itself (`WebFetch` failed in this sandbox both times it was tried).
  Flagged to the user as a lighter-than-usual verification; they accepted it as-is.
- **Supplier name/address/phone**: the plan assumed `IdentifierKeys.SUPPLIER` was a
  single flat key with nowhere to put structured contact info, and asked whether to add
  a composite key. Turned out not to be the right question - the user's actual design is
  that `SUPPLIER`'s value should be a **PAC-ID** for the supplier itself, whose own
  attribute page carries its own name/address/phone. No new key needed:
  `attribute_row()` already renders any attribute value that resolves as a PAC-ID via
  the existing `reference()` macro (an HTMX-loaded card), so this works today with zero
  template-level special-casing - confirmed in the smoke test below.
- **Package quantity**: `CommercePackagingKeys.QUANTITY` (`schema.org/quantity`)
  reused as-is - it already lives in the packaging-keys class, no CLP-specific key
  added.
- **EUH statements**: reused `RegulatorySafetyKeys.GHS_HAZARD_STATEMENT` rather than a
  dedicated key - EUH and H-statements render identically (a code + text), and the
  smoke test below includes one of each under the same key to confirm.

**Alternatives considered / why not:**

- A dedicated `CLP_SUPPLIER_INFO` composite key holding name+address+phone as one
  structured value - rejected once the PAC-ID-reference design was clarified: it would
  have duplicated data that already belongs on the supplier's own PAC-ID page, and
  broken the existing generic reference-rendering path for no benefit.
- Deduplicating the highlighted hazard/supplier/quantity/SDS attributes out of the
  generic "Attributes" section further down the page (so nothing appears twice) -
  not attempted in this pass. `attribute_group_block(ag)` only supports hiding whole
  groups (`hide_attribute_groups`), not individual attributes within a group, and
  building a per-attribute exclusion mechanism felt like more machinery than this
  first skeleton warranted. Flagged in [[developer-docs/TODO.md]] as a known
  simplification, not a silent gap.

**Verified (not just assumed):** rendered the full template end-to-end via a
standalone `jinja2.Environment` against a real `PacInfo`/`pyAttributeGroup`/
`pyAttribute` fixture with a signal word, two hazard statements (one H-, one
EUH-coded, same key), a precautionary statement, a UFI, a `pyReference`-valued
supplier, a quantity, and an SDS URL - confirmed no exceptions, the hazard block
renders first (right after the product-identity card), the supplier value renders
through the reference-card path (not as plain text), and the SDS URL renders as an
actual link (via the existing `is_url` predicate).

**Also found while building the smoke-test fixture, unrelated to Phase 4b, not
fixed:** `PacInfo.safety_pictograms` (`app/pac_info/pac_info.py:195-197`) filters
attributes whose key contains `"https://labfreed.org/ghs/pictogram/"`, a completely
different URI from `RegulatorySafetyKeys.GHS_PICTOGRAM`
(`"https://www.wikidata.org/wiki/Q19360817"`) - the well-known-key registry and the
actual pictogram-lookup logic disagree on what a pictogram's key looks like. And
separately, `base-components.jinja.html`'s `attribute_group_block(ag)` macro reads
`ag.label`/`ag.origin`, and `pac_info.jinja.html`/`digital_label.jinja.html`'s loops
read `ag.key` - but `pyAttributeGroup` (via `AttributeGroup`) only has `group_label`/
`group_key` fields, not `label`/`key`. Jinja's default (non-strict) `Undefined`
swallows this silently - `{{ ag.label }}` renders blank instead of raising, and `ag.key
not in hide_attribute_groups` is always true - so this has apparently been rendering
blank group headings and never actually hiding a group on the real landing page all
along, not just in this new template. Both flagged in
[[developer-docs/TODO.md]] rather than fixed here - out of scope for Phase 4b, and the
second one in particular touches code this plan's earlier phases already touched
without either of us noticing it.

*Investigated 2026-07-31, Phase 4b of the PAC-ID Attributes improvement plan
(`plans/pac-id-attributes-implementation-is-distributed-pelican.md`), on branch
`cleanup-labfreed-library-for-release-1.0.0`.*

---

## GHS hazard/precautionary statement text + pictogram lookup, sourced from UNECE Annex 3

**Decision:** hazard and precautionary statement attribute values (`RegulatorySafetyKeys.
GHS_HAZARD_STATEMENT`/`GHS_PRECAUTIONARY_STATEMENT`) are expected to carry bare codes
(`"H225"`, `"P210"`, or combined codes like `"H300+H310"`), not pre-formatted text - the
digital label resolves the code to its official text and (for hazard statements) pictogram
via a new static lookup table, rather than requiring whoever populates the attribute data to
also maintain that text themselves. Landed as:

- `labfreed/utilities/ghs/ghs_statements.json` - transcribed directly from the
  user-provided **UNECE GHS Rev.7 (2017) Annex 3** PDF (the official source, not a
  third-party summary): all ~72 individual + ~17 combined hazard statement codes (H2xx/
  H3xx/H4xx), all ~60 individual + ~35 combined precautionary statement codes (P1xx-P5xx),
  the 9 `GHS0x` pictogram codes, and a `hazard_statement_pictograms` table mapping each
  H-code to its pictogram(s) + signal word, reconstructed from Annex 3 Section 3's
  per-hazard-class tables (e.g. "FLAMMABLE LIQUIDS, category 2 -> Flame, Danger, H225").
- `labfreed/utilities/ghs/ghs_statements.py` - thin cached-loader accessor module.
  Originally placed alongside `unece_units.py` in `well_known_keys/unece/`, moved to
  its own `utilities/ghs/` subfolder since it isn't a key registry at all (no keys, no
  enum) - it's a data+accessor utility, given its own subfolder (rather than sitting
  flat alongside `translations.py`/`base36.py`) so the `.py`+`.json` pair stays
  together as a unit. Exposes `hazard_statement_text`/`precautionary_statement_text`
  (code -> official text), `pictogram_codes_for_hazard_statement` (code -> list of
  `GHS0x` codes, splitting combined codes and unioning each constituent's pictograms),
  and `signal_word_for_hazard_statement`.
- New `hazard_statement_row(code)`/`precautionary_statement_row(code)` macros
  (`base-components.jinja.html`) render one table row per code: pictogram icon(s) +
  code + resolved text, used by `digital_label.jinja.html`'s hazard block in place of
  the generic `attribute_row` for those two specific fields.

**Why:** the same rationale as the earlier UFI/quantity/supplier decisions - keep
regulatory text and code/pictogram associations as a single maintained-by-us lookup
table (matching how `well_known_keys/unece/UneceUnits.json` already works for UCUM
units), not something every issuer's data source has to carry or every attribute
value has to spell out in full.

**Alternatives considered / why not:**

- An existing PyPI/npm package for this - searched first (`ghs-hazard-pictogram`,
  `ghs-hazard-pictograms`, `veriCAS`). None fit: the two pictogram packages are icon
  **asset** libraries (the 9 GHS images), not a code->text->pictogram mapping;
  `veriCAS` does live PubChem-backed per-substance lookups, a different shape of
  problem entirely. Rejected in favor of vendoring the official table ourselves.
- Deriving the table from web search summaries instead of the primary source -
  rejected once it became clear `WebFetch` couldn't reach any external page in this
  sandbox (confirmed via repeated real connection failures across 5 different
  domains, not a one-off) - summarized snippets aren't reliable enough to build a
  safety-compliance table from. Waited for the user to supply the actual PDF instead.

**Known limitation, not fully resolved:** pictogram assignment is technically per
**hazard class and category**, not per individual H-code - a handful of codes (H221,
H229, H261, H272, and the category-3 acute-toxicity codes) are assigned to more than
one category with a different pictogram/signal word each. `hazard_statement_pictograms`
picks one default pairing per code (documented in the JSON's own `_comment` key) rather
than modeling the full classification matrix - correct for the common case, an
approximation for the rest. Also: **EUH statements** (EU CLP-specific supplemental
hazard statements, e.g. `EUH208`) aren't in this table at all - they come from EU CLP
Annex II, a different document than the UN GHS Annex 3 the user provided. Looking one
up falls back to displaying the bare code with no resolved text or pictogram, rather
than erroring. Flagged in [[developer-docs/TODO.md]].

**Verified:** re-ran the earlier digital-label smoke test with hazard statement values
`["H225", "H300+H310", "EUH208 Contains X"]` - confirmed `H225` resolves to its Flame
pictogram and official text, the combined `H300+H310` resolves to the Skull-and-
crossbones pictogram and combined text (this caught a real bug on the first pass - see
below), and the unresolvable `EUH208` falls back to displaying the raw value with no
exception.

**Bug caught by that verification, fixed same pass:** the first implementation stored
multi-pictogram entries (only H241 needs this - "Exploding bomb and flame") as a
single string and split on `" and "` to recover the individual pictogram names. That
collided with pictogram names that themselves contain "and" - `"Skull and crossbones"`
split into `["Skull", "crossbones"]`, neither of which matched anything, silently
dropping the pictogram for every H-code whose pictogram is Skull-and-crossbones
(H300, H301, H310, H311, H330, H331, and their combined statements). Fixed by storing
`pictogram` as a proper list in the JSON (`["Exploding bomb", "Flame"]` for H241,
single-element lists everywhere else) instead of a string to split - removes the
ambiguity structurally rather than special-casing it.

*Investigated 2026-08-03, on branch `cleanup-labfreed-library-for-release-1.0.0`.*

---

## HTML sanitization for attribute values: `nh3`, an allowlist, and an always-superscript rule

**Decision:** attribute values may contain a small set of inline HTML formatting tags
(`sub`, `sup`, `i`, `em`, `pre` - e.g. `"C<sub>6</sub>H<sub>12</sub>"`) which now render
as actual HTML instead of literal escaped text. A new `render_text()` helper
(`lib/render_predicates.py`) sanitizes the value through `nh3.clean()` with that
explicit tag allowlist and `attributes={}` (no attributes allowed on any tag, not even
the allowed ones), then wraps the result in `markupsafe.Markup` so Jinja doesn't
re-escape it. Wired into `attribute_row`'s plain-text value branch only (not every
table cell in the codebase - `key_value_table`/`card_info_block` still render plain
escaped text). Also added: a registered-trademark symbol (`®`) in any value is always
wrapped in `<sup>®</sup>`, even in a value with no markup around it at all, applied
before sanitization so the inserted tag still passes through the same allowlist path.

**Why:** the request was specifically "needs to be sanitized... scripts and style and
other tags can be stripped" - a real XSS surface, not just a formatting nicety. A
regex-based allowlist (matching literal `<sub>...</sub>` patterns) would be the
naive approach but is a known-unreliable way to sanitize HTML - it doesn't understand
nesting, and critically doesn't strip **attributes** on otherwise-allowed tags, e.g.
`<sub onmouseover="...">` would sail through a regex tag-matcher untouched. `nh3` is a
real HTML-parser-based sanitizer (Rust/`ammonia`, the same engine PyPI itself uses for
README rendering) that strips disallowed tags *and* all attributes correctly.

**Alternatives considered / why not:**

- `bleach` - the more historically well-known Python sanitizer, considered first since
  it's more widely recognized. Not chosen: it wraps `html5lib` and has been in reduced
  maintenance for a while; `nh3` is the more actively-maintained, faster (compiled),
  and equally strict modern choice for exactly this "strict allowlist, strip
  everything else" use case.
- A regex-based tag allowlist with no dependency at all - rejected outright, see Why
  above (attribute-based XSS vectors slip through unchanged).
- Marking the whole value `| safe` in the template and trusting the data source not to
  send anything dangerous - rejected: attribute values come from arbitrary upstream
  data sources (an issuer's own attribute server, a supplier's feed), not code this
  package controls: they're exactly the untrusted-input case autoescaping exists for.

**Verified (not just assumed):** ran `nh3.clean()` directly against a small adversarial
set before wiring it in - confirmed `<script>...</script>` content is fully removed
(not just unwrapped), `<sub onmouseover="alert(1)">` keeps the tag but drops the
attribute, `<a href="javascript:...">` is unwrapped to plain text, and legitimate
`<sub>`/`<i>` markup passes through unchanged. Re-ran the full digital-label smoke test
with a value containing a `<script>` tag, a `<sub>` tag, an `<i>` tag, and a bare `®`
mixed together - confirmed the script and its content disappeared entirely, `<sub>`/
`<i>` rendered as real HTML, and `®` came out wrapped in `<sup>`.

**Impact:** new dependency, `nh3>=0.2.18`, added to the `extended` extra in
`pyproject.toml` (the same extra `Flask`/`Flask-Cors` already live in, since this is a
web-rendering-only concern) - not a core dependency, only pulled in by pip installs
that opt into `labfreed[extended]`, same as everything else `pac_issuer_lib` needs.

*Investigated 2026-08-03, on branch `cleanup-labfreed-library-for-release-1.0.0`.*

---

## Three attribute-rendering bugs found and fixed while testing real-world data shapes

**Decision:** three separate, real bugs in `lib/render_predicates.py`/
`base-components.jinja.html` surfaced while testing against realistic values (a CDN
image URL, a data source's own "code + description" statement text) rather than the
clean synthetic fixtures used earlier - all fixed:

1. **`is_url()` missed every `pyResource` value.** It required
   `isinstance(s, str)`, but `pyResource` is a `RootModel[str]` - a URL by
   construction, but not a `str` instance. Any `pyResource`-typed value that also
   failed `is_image()`'s extension check (see #2) fell all the way to the plain-text
   branch - a real link rendered as inert text. Fixed by extracting the URL string
   from either a `pyResource` or a plain `str` before running the URL check.
2. **`is_image()`'s extension check broke on query strings.** It matched the
   suffix of the *entire* value string, but real CDN asset URLs (e.g. carlroth.com's
   product images) route through a long tracking/context query parameter after the
   real extension - `...7342.jpg?context=<base64>` doesn't end in `.jpg` as a raw
   string. Fixed by checking `urlparse(value).path`'s suffix instead of the whole
   string.
3. **`is_reference`/`is_url` were checked in the wrong order** in `attribute_row`'s
   value dispatch (`is_image` -> `is_url` -> `is_reference` -> else). A PAC-ID is
   itself always a valid URL, so a bare PAC-ID **string** (not wrapped in
   `pyReference`) always matched `is_url` first and never reached the reference-card
   path - only `pyReference`-wrapped values (which fail `is_url`'s old `isinstance
   (s, str)` check) got the card. Reordered to `is_image` -> `is_reference` -> `is_url`
   -> else, matching the label-side (`th`) dispatch, which already had this right.

**Also fixed, same investigation:** hazard/precautionary statement values are
expected to be a bare code, but a real data source is more likely to send
`"H225 - Highly flammable liquid and vapour"` (code + its own copy of the text) than
a bare `"H225"`. The row macros did an exact dict lookup on the *whole* value, missed,
and fell back to showing that same whole value in both the code and text columns - a
visually "duplicated" row, with an empty pictogram cell (a whole-string cache miss
also fails the pictogram lookup). Fixed with a new `extract_statement_code()`
(`utilities/ghs/ghs_statements.py`): pulls the leading code(s) off the front,
lenient about the separator between the code and any trailing text (blank space,
`-`, `;`, `.`, any run of these) but never treating `+` as that separator, since `+`
is reserved for joining codes into one combined statement (e.g. `"H300+H310"`). Colon
is deliberately *not* in the separator set - several P-statements' own official text
ends in a colon (e.g. `"IF SWALLOWED:"`), so treating it as a strip-me separator would
corrupt real statement text, not just a data source's redundant copy of it. The row
macros now show the *clean extracted code* in the code column, and fall back to the
*original raw value* (not the bare code) in the text column when the extracted code
doesn't resolve - so an unresolvable code (e.g. an EUH code, see the earlier GHS
lookup entry) still shows whatever text the data source gave it, rather than a bare
unexplained code.

**Verified:** re-ran the digital-label smoke test with the exact carlroth.com image
URL (now renders as an actual `<img>`, confirmed via a fresh `is_image`/`is_url` check
before and after the fix), a bare PAC-ID string value (confirmed it now reaches
`reference()`), and hazard statement values written as `"H225 - ..."` and
`"H314; ..."` (confirmed both resolve to their clean code, correct text, and correct
pictogram - no more empty/duplicated cells).

*Investigated 2026-08-03, on branch `cleanup-labfreed-library-for-release-1.0.0`.*

---

## Hazard-row pictograms prefer an explicit attribute over the code-derived guess

**Decision:** `hazard_statement_row()` now takes a second `explicit_images` argument
- a `{GHS0x: image_url}` dict built by a new `explicit_pictogram_images(pac_info)`
(`lib/render_predicates.py`), which reads whatever pictogram attributes the data
source directly supplied via the existing `PacInfo.safety_pictograms` mechanism
(keyed like `"https://labfreed.org/ghs/pictogram/GHS02"` - confirmed against a real
usage in `examples/pac_mettorius_com/attribute_datasources.py`). For each pictogram a
row needs, it's looked up in `explicit_images` first; only falls back to the static
`ghs0x.png` asset (derived from the H-code via `pictogram_codes_for_hazard_statement`)
when the data source didn't supply that one directly.

**Why:** the code-derived guess has a known, documented ambiguity (a handful of
H-codes are assigned to more than one hazard category, each with a different
pictogram) - see the earlier "GHS hazard/precautionary statement..." entry. A data
source that already knows the substance's actual classification can supply the
correct pictogram directly with no ambiguity at all; preferring that whenever it's
available removes the approximation for exactly the cases where better information
exists, while still degrading gracefully (falls back to the derived guess) when it
doesn't.

**Verified:** rendered with one attribute group holding both a `GHS_HAZARD_STATEMENT`
value (`H225`) and an explicit `.../pictogram/GHS02` attribute pointing at a
made-up custom icon URL, alongside a second hazard statement (`H400`) with no
matching explicit attribute - confirmed `H225`'s row used the custom URL verbatim, and
`H400`'s row fell back to the static `ghs09.png` path.

*Investigated 2026-08-03, on branch `cleanup-labfreed-library-for-release-1.0.0`.*

---

## GHS statement text is now keyed per-language (English only, for now)

**Decision:** `ghs_statements.json`'s `hazard_statements`/`precautionary_statements`
changed from `{code: "text"}` to `{code: {"en": "text"}}`. `hazard_statement_text()`/
`precautionary_statement_text()` both gained an optional `lang='en'` parameter,
falling back to English if the requested language isn't present for that code.

**Why:** the user asked for translations to be added, but no verified non-English
text was available to add safely - fabricating translations for safety-critical
regulatory text carries real accuracy risk, the same reasoning that applied to
sourcing the English text itself from the primary UNECE document rather than a
summary. Landed the schema change now (mechanical, zero risk) so a future language
can be added as pure data with no further code changes, without pretending to have
solved translation content that doesn't exist yet.

**Not done:** no actual non-English content. Needs an authoritative per-language
source the same way the English text did (e.g. EU CLP Annex III, which is officially
published in every EU language for exactly this purpose) - flagged in
[[developer-docs/TODO.md]] rather than guessed at.

*Investigated 2026-08-03, on branch `cleanup-labfreed-library-for-release-1.0.0`.*

---

## GHS pictogram icons: flat filenames, not a `ghs/` subdirectory

**Decision:** the GHS pictogram PNGs live directly in `pac_issuer_lib/static/`
(`ghs01.png`...`ghs08.png`), not under a `static/ghs/` subdirectory as first
implemented. `hazard_statement_row()` calls `resolve_static_image(code.lower())` -
no path prefix, no extension.

**Why:** `resolve_static_image()` (`app_factory.py:179`) only ever searches flat
filenames directly in the static root: it does `Path(base_name).stem` on its input
(which silently discards any directory component - `Path('ghs/ghs02.png').stem` is
`'ghs02'`, not `'ghs/ghs02'`) and then matches candidate files via `folder.iterdir()`
(no recursion into subdirectories) against a regex built from that stripped stem.
Every other icon in this codebase already relies on this - `card_image()` calls
`resolve_static_image('cat' + category.key + '.svg')`, a flat name, never a path.
The first implementation of this feature put the pictogram files under a `ghs/`
subdirectory and passed `'ghs/' + code + '.png'`, which silently never matched
anything - not a crash, just a permanently-missing image, since a missing match
returns `None` and an `<img src="None">` just fails to load like any other broken
image reference.

**Alternatives considered / why not:**

- Make `resolve_static_image()` support subdirectories - rejected: it's shared
  infrastructure every other icon call site in this codebase depends on; changing
  its search behavior is a bigger, riskier change than just following the
  convention it already has (flat names), especially while this exact area of the
  code is under active concurrent editing elsewhere in the same session.

**Verified:** this was caught by the user actually testing the real rendered popup
("the flame is not found"), not by any of this feature's own smoke tests - those all
stubbed `resolve_static_image` with a trivial `lambda name: f'/static/{name}'` that
happily accepted a path with a slash in it and never exercised the real function's
flat-search-only behavior at all. After moving the files and dropping the path
prefix, re-verified by replicating the real function's exact matching regex against
the actual static directory directly (rather than via another stub) - confirmed
`ghs02` -> `ghs02.png`, `ghs09` -> `None` (the one file still missing, as already
flagged).

*Investigated 2026-08-03, on branch `cleanup-labfreed-library-for-release-1.0.0`.*

---

## Naming cleanup, `digital_label.jinja.html` relocated, and pictograms moved to a deduplicated strip

**Decision:** three cleanups requested together:

1. **`digital_label.jinja.html` moved** from its own `templates/digital_label/`
   subdirectory into `templates/pac_info/` (alongside `pac_info.jinja.html`,
   `card.jinja.html`, etc.) - a whole subdirectory for one file wasn't warranted.
   `pac_issuer_landing_page.jinja.html`'s `{% include %}` path updated to match; the
   file's own internal imports (`"pac_info/base-components.jinja.html"` etc.) needed
   no change, since Jinja import paths in this codebase are already always full
   paths from the template root, not relative to the importing file.
2. **Two confusingly-named macros renamed**: `service_table_section` ->
   `service_links`, `services_table` -> `service_group_block`
   (`base-components.jinja.html`). Neither old name matched what it rendered (both
   emit `<div>`s, not `<table>`s), and the pairing read backwards - "table" named
   the *inner* piece, "section" the outer wrapper. `service_group_block` also
   matches the already-established `_block` naming for a titled wrapper section
   (`category_block`, `attribute_group_block`). Checked for external call sites
   first - `service_table_section` had none; `services_table` was called directly
   by `labfreed-webtools/pac_issuer_demo/acme_labs`'s own `pac_info.jinja.html`
   override, so that call site was updated too as part of this same change (per
   this plan's standing policy #3, webtools call-site updates are in scope).
3. **`card_info_block`'s parameter renamed** `dict` -> `segments`
   (`card-components.jinja.html`) - naming a parameter after its own builtin type is
   exactly the kind of naming an LLM tends toward and a human wouldn't choose. Purely
   internal (the macro is only ever called positionally), so no call-site changes
   needed - confirmed `labfreed-webtools/pac_issuer_demo/acme_labs`'s own
   independent copy of this macro (a separate file entirely, not calling into the
   package's version) is unaffected either way.

**Also, a real design change, not just naming:** hazard/precautionary statement
pictograms moved from a per-row column to a single deduplicated strip shown once
above the table. A new `hazard_pictogram_codes(pac_info, attributes)` (`lib/
render_predicates.py`) collects the pictogram(s) for every hazard/precautionary
statement value across the given attributes (precautionary codes simply contribute
none - they have no pictogram of their own) plus whatever's explicitly supplied on
`pac_info`, puts them in a `set()` to dedupe, and returns them `sorted()` by GHS
number. A new `pictogram_strip()`/`pictogram_image()` pair of macros
(`base-components.jinja.html`) render that list once; `hazard_statement_row()`/
`precautionary_statement_row()` dropped their per-row pictogram cell entirely - both
are now plain two-column (code, text) rows. This also supersedes the old
`card_macros.safety_pictograms(pac_info)` call in the hazard section (removed) - the
new strip is a strict superset of what that showed, since it already folds in
`pac_info`'s explicitly-supplied pictograms via the existing `explicit_pictogram_
images` helper.

**Why:** a hazard statement's pictogram is a property of the *substance*, not of any
individual statement row - several codes routinely share the same one (H300/H310/
H330 are all Skull-and-crossbones), so repeating it on every row was redundant, and
sidesteps needing per-row precision for the handful of codes with genuinely
ambiguous category-dependent pictogram assignment (see the earlier "GHS hazard/
precautionary statement..." entry) - deduplicating by GHS code rather than by
statement code makes that ambiguity moot for display purposes.

**CSS follow-up:** `.lf-ghs-pictogram` resized from an inline-text-sized icon
(`1.5em`, meant to sit next to a code/text column) to a standalone `3rem` icon in a
new `.lf-ghs-pictogram-strip` flex container - it's the section's main visual
callout now, not an inline decoration. The now-orphaned `.lf-ghs-pictogram--blank`
placeholder rule (for the removed per-row empty-pictogram-cell case) was deleted -
confirmed zero remaining references before removing it.

**Verified:** rendered with `["H225", "H300", "H310", "H330"]` (three of which share
one pictogram) plus a `P210` - confirmed the strip shows exactly two pictograms
(Flame, Skull-and-crossbones) in GHS-number order, and every row (both hazard and
precautionary) is a clean two-column `code | text` pair with no pictogram cell.

*Investigated 2026-08-03, on branch `cleanup-labfreed-library-for-release-1.0.0`.*

---

## GHS statement rows reuse `.lf-th--label`/`.lf-td--val`, not their own classes

**Decision:** `hazard_statement_row()`/`precautionary_statement_row()` now emit
`<th class="lf-th lf-th--label">{{code}}</th>` / `<td class="lf-td lf-td--val">
{{text}}</td>`, replacing the custom `lf-ghs-row__code`/`lf-ghs-row__text` classes.

**Why:** every other key/value table in this codebase (`key_value_table`,
`attribute_row`) already gets a 1/3 vs 2/3 column split and bold labels for free
from `.lf-table--kv th.lf-th--label { width: 33%; font-weight: 600; }` /
`.lf-table--kv td.lf-td--val { width: 67%; }` (`styles_pac_info.css`) - a rule that
already existed. The GHS rows' own `lf-ghs-row__code`/`lf-ghs-row__text` classes
just never matched that selector, so the table silently fell back to equal-width
columns instead of matching every other table on the page. Reusing the existing
classes fixes it with no new CSS at all, rather than duplicating the same
33%/67% rule under a GHS-specific selector.

**Verified:** rendered a hazard statement row and confirmed the emitted markup uses
`th.lf-th--label`/`td.lf-td--val` exactly as `attribute_row` does.

*Investigated 2026-08-03, on branch `cleanup-labfreed-library-for-release-1.0.0`.*

---

## Same-process action calls dispatch in-process, not over real HTTP

Related to: ["Well-known action handler: `action-generic` params travel as plain query
params, not through the CIT
template"](design-choices.md#well-known-action-handler-action-generic-params-travel-as-plain-query-params-not-through-the-cit-template)

**Decision:** a Flask app that both hosts `labfreed_experimental.actions`' Flask layer
(`flask_layer.py`) *and* is itself the caller resolving/invoking those actions (e.g.
`labfreed-webtools`' `instrument_demo`, syncing its own Signals inventory through the
well-known actions it also serves) should detect when
`pac_info.get_action_by_intent(intent).url` resolves to its own base URL, and in that
case dispatch in-process via Werkzeug's/Flask's own test client (`app.test_client()` /
`werkzeug.test.Client`) instead of a real `requests.post()` back into itself. Anything
that resolves elsewhere still goes out as a normal HTTP request - the call site doesn't
need to know or care which path was taken. See the new
`labfreed_experimental/actions/README.md` for the documented `call_action()` shape any
such consumer should implement (not shipped by this package itself - see the
alternatives below).

**Why:** the user reported that this app's real deployment (Azure App Service) "does
not like to call itself" for this pattern - App Service's default sync-worker pool is
small/single, so a request handler that blocks waiting on an HTTP call back into the
same app has no free worker left to serve that inbound request: a real deadlock risk,
not just wasted overhead. Confirmed (via the Werkzeug/Flask docs, not a live
reproduction) that Werkzeug's `test.Client` - what `Flask.test_client()` itself
subclasses - drives a WSGI app directly through the Python call stack: no socket, no
separate worker, while still exercising the exact same dispatch a real HTTP call would
(routing, blueprints, before/after-request hooks, error handlers).

**Alternatives considered / why not:**
- `requests-wsgi-adapter` (`wsgiadapter.WSGIAdapter`, mounted onto a `requests.Session`
  so the *same* `session.post(url)` call transparently dispatches in-process) - would
  let call sites use one uniform `requests`-shaped API for both local and remote
  dispatch, but its PyPI/GitHub listing shows it as unmaintained (last checked
  2026-08-03); rejected in favor of Werkzeug's own actively-maintained,
  already-a-dependency mechanism.
- Always call over real HTTP regardless of destination - rejected because of the
  self-deadlock risk above.
- Ship a shared `call_action()` helper directly in this package instead of just
  documenting the pattern - rejected for now: the helper needs the consuming app's own
  `Flask` instance and its own notion of "my base URL," and there's only one real
  consumer (`instrument_demo`) to generalize an API from so far. See
  `developer-docs/TODO.md`, "Promote `instrument_demo`'s `call_action()` dispatch
  helper into this package," for revisiting once a second consumer needs it.

**Impact:** only matters for a consumer that is *also* the CIT-resolved destination for
its own action calls - a pure external caller (e.g. a scanning client resolving someone
else's actions) always goes out over real HTTP and never hits this code path. The
concrete implementation of this pattern lives in `labfreed-webtools`'
`instrument_demo/action_client.py`, deliberately kept local to that app rather than in
this package (see the alternative above).

*Investigated 2026-08-03, while wiring `instrument_demo` up as a real `action-generic`
consumer of its own CIT - it previously called `SignalsActionBackend` directly,
bypassing CIT resolution entirely.*

---

## Issuer-configured contact address (`SiteMeta.contact_address`), alongside the existing supplier-PAC-ID design

**Decision:** `SiteMeta` (`app_factory.py`) gained a new optional field,
`contact_address: str | None`. Rendered as plain text (via a new
`.lf-issuer-contact-address { white-space: pre-line; }` rule so a natural
multi-line address string breaks visually without needing embedded HTML) in its own
"Supplier Contact" section on the digital label, positioned **below the Safety Data
Sheet section** (a deliberate placement call, revised from an initial pass that put
it inside "Supplier & Quantity" further up the page) - separate from, and
independent of, the existing `SUPPLIER` attribute/PAC-ID-reference rendering in
"Supplier & Quantity". Neither is required; each shows only if present. No new
plumbing needed beyond the field itself: `SiteMeta` is already dumped into
`bp._jinja_env`'s globals once per blueprint (`_build_jinja_env`), so `site_meta.
contact_address` is automatically available in every template this blueprint
renders, the same way `navbar.jinja.html` already reads `site_meta.nav_items`.

**Why:** revisits the earlier "supplier should be a PAC-ID" decision - the user
still endorses that design for the case where the supplier is a *different* entity
from the issuer (e.g. a distributor's page referencing another company's product,
where a PAC-ID reference card is the right way to show that other company's own
name/address/phone). But for the common case where the issuer *is* the supplier
(a manufacturer running their own PAC-ID issuer site), requiring a whole separate
PAC-ID and its own populated attributes just to show that same company's own
address is unnecessary indirection - the issuer can just configure it once, and every
product page on their site shows it automatically.

**Alternatives considered / why not:**

- A structured `contact_name`/`contact_address`/`contact_phone` split (mirroring
  `MetaAttributeKeys.PHONE`/`ADDRESS`/`COUNTRY` on the attribute side) - not chosen
  for this pass: every other `SiteMeta` field (`site_title`, `site_author`, etc.) is
  a single plain string, and the user's own phrasing was specifically about "the
  address," not three separate fields. A free-text block the issuer formats
  themselves (name and phone as extra lines, if wanted) matches that simplicity and
  is a cheap field to split later if a real need for structure shows up.
- Rendering `contact_address` through `render_text()` (the sanitizer used for
  attribute values) - rejected: that helper's allowlist (`sub`/`sup`/`i`/`em`/`pre`,
  no `<br>`) exists to sanitize *untrusted* attribute data, and would actively fight
  a multi-line address rather than help. `contact_address` is issuer-owned config,
  set in the issuer's own Python call to `create_blueprint(site_meta=...)`, not
  attacker-controlled input - it doesn't need that sanitizer, just Jinja's normal
  auto-escaping (which it still gets) plus a CSS rule to preserve newlines.

**Verified:** rendered the digital label with both a `SAFETY_DATA_SHEET` attribute
and `site_meta.contact_address` set - confirmed "Safety Data Sheet" appears earlier
in the output than "Supplier Contact", and separately confirmed the contact section
still renders correctly with no `SUPPLIER` attribute present at all (each section's
visibility is independent, neither requires the other).

*Investigated 2026-08-03, on branch `cleanup-labfreed-library-for-release-1.0.0`.*

---

## `@experimental` decorator (`labfreed_infrastructure.py`), adapted from Apache Beam rather than pandas

**Decision:** added `experimental(reason: str = "")` to `labfreed_infrastructure.py`
(exported from `labfreed` via its existing `from labfreed.labfreed_infrastructure import
*`). It decorates a function, method, or class - wrapping functions/methods with
`functools.wraps` and patching a class's `__new__` (the same technique the `deprecated`
package already uses under the hood for `@deprecated`, and already proven safe on
Pydantic models in this codebase, e.g. `response.py`'s `AttributesOfPACID`) - and on
every call/instantiation emits a plain builtin `FutureWarning` plus appends a
`**Experimental:** ...` note to the docstring. Calling convention deliberately mirrors
the existing `@deprecated("reason")` usage (the `deprecated` PyPI package, already used
in ~15 places) for consistency: `@experimental("reason")`.

This is distinct from the existing `labfreed_experimental/` package (BLE PAC discovery
etc.): that folder is for whole modules with no compatibility guarantee at all, while
`@experimental` flags one function/method/class inside a module that is otherwise
stable and normally covered by the deprecate-first policy. README's Versioning section
gained one sentence exempting `@experimental`-marked APIs from that policy - they can
change or vanish in a minor/patch release without a deprecation cycle.

**Why:** the user asked to "copy the `@experimental` decorator pattern from pandas."
Checking pandas' actual source first (see Alternatives) showed pandas has no such
decorator - it exists purely as a docstring convention. Rather than build something and
call it "the pandas pattern" when pandas doesn't have one, this was surfaced to the
user, who chose to base it on Apache Beam's real `apache_beam.utils.annotations`
instead.

**Alternatives considered / why not:**

- **pandas' own convention** - verified empirically, not assumed: cloned
  `pandas-dev/pandas` (sparse checkout of `pandas/`) and grepped the full tree, plus
  fetched `pandas/util/_decorators.py` at `main` and tags `v0.23.4` through `v2.2.3`
  directly from GitHub. No `experimental` decorator or `Experimental`-named class exists
  anywhere in the checked versions. Every "experimental" hit is a plain docstring
  sentence like *"ArrowDtype is considered experimental. The implementation and API may
  change without warning."* - no runtime warning, no programmatic marker at all. Not
  usable as "the pandas pattern" because it doesn't exist as a pattern beyond prose.
- **Apache Beam's `experimental`** (`apache_beam.utils.annotations`) - read the real
  source (fetched from GitHub at several tags). It's a `functools.partial` of a shared
  `annotate(label, since, current, extra_message, ...)` function also used for
  `deprecated`, with a `_WarningMessage` class building the text and a class/function
  branch nearly identical to what `deprecated` (the PyPI package) already does in this
  codebase. Chosen as the base pattern - it's the real, working prior art the user
  wanted, and its mechanism already has a proven analog here via `deprecated`.
  Deliberately deviated from Beam in two spots: (1) Beam only appends a docstring note
  for `label='deprecated'`, not for `experimental` - looked like an oversight, so this
  implementation documents both; (2) Beam uses a plain builtin `FutureWarning` for
  `experimental` (only `deprecated` gets a custom warning subclass,
  `BeamDeprecationWarning`) - kept that asymmetry since it mirrors how `@deprecated` is
  already used in this codebase (plain builtin `DeprecationWarning`, no custom
  subclass). Note: Beam itself removed `experimental` from its own codebase somewhere
  around v2.4x-v2.50 (confirmed present at `v2.40.0`, gone by `v2.50.0`) - only
  `deprecated` remains upstream today.
- **Dagster's `@preview`/`@beta` lifecycle annotations** (`dagster._annotations`,
  read via GitHub) - a heavier system: dedicated `PreviewInfo`/`BetaInfo` data objects
  plus introspection helpers (`is_preview()`, `get_beta_info()`, etc.), replacing an
  older `@experimental` Dagster itself used to have. Offered to the user as an
  alternative; not chosen for this pass - more machinery than a single-repo library
  with one experimental-marking need currently justifies.
- **PEP 702's `warnings.deprecated`** (`typing`/`typing_extensions`) - not applicable
  here: it's specifically for deprecation (type checkers flag call sites as going
  away), not for "newly added, still shifting" - the opposite lifecycle stage.

**Verified:** ran the decorator locally (function, method, and class cases) with
`python3 -W always` - confirmed the `FutureWarning` fires with the correct message and
points at the actual call site (not at the decorator's own wrapper frame), and that the
docstring gains the `**Experimental:**` note while undecorated methods on the same
class are untouched.

*Investigated 2026-08-04.*

---

## PAC-CAT segment/category context (issuer, issuing system) must be re-derived on every `.segments` access, not cached on the segment instance

**Decision:** While designing per-segment `issuer`/`issuing_system` accessors for
`CategorySegment` (alongside the existing `derivation_namespace`, for the PAC-CAT
derivation-namespace-issuing-system work), don't denormalize them onto a segment
object once and read them back later. `PredefinedCategory.segments`
(`predefined_categories.py:31-38`, via `_get_segments_canonical`/
`_get_segments_from_bindings`) and `PAC_CAT.categories` (`pac_cat.py:26-34`) already
rebuild fresh `CategorySegment`/`Category` instances on *every* access - no caching,
already relied on elsewhere (see the "no caching" comment in
`test_PAC_CAT_main_category_and_processor.py`'s `test_main_category_is_the_first_category`).
Any context tagged onto one instance is gone the moment `.segments`/`.categories` is
called again, even on the same `PAC_CAT`. So `issuer`/`issuing_system` must be
recomputed by the rebuild functions themselves, every time they run, from state cached
on the stable `Category` object the caller actually holds onto - not from state
stashed on the transient segment objects those functions emit.

**Why:** `derivation_namespace` already gets this half-right, somewhat by accident.
`_get_segments_from_bindings` reads it off the *original* tagged segment stored in
`_segment_bindings` (itself cached on the `Category`, set once in
`_cat_from_cat_segments`), so it survives repeated `.segments` calls. But
`_get_segments_canonical` (the no-marker path) never threads `derivation_namespace`
through at all - harmless today only because that path is only ever used when there's
no marker, so the value is always `None` regardless. Adding `issuer` (needs the base
PAC-ID's own issuer) and `issuing_system` (needs a *sibling* category, which doesn't
exist yet when the primary category is built) hits the same gap in a way that's no
longer harmless by coincidence - both rebuild paths need to actively participate.

**Alternatives considered / why not:**

- Denormalize `issuer`/`issuing_system` directly onto each `CategorySegment` at
  construction time (the original plan going into this investigation) - rejected once
  the rebuild-on-every-access behavior was confirmed by reading `predefined_categories.py`:
  it would work for the one set of segment objects built during that pass, but the very
  next `.segments` access on the same category discards them and builds new, untagged
  ones.
- Add real memoization to `.segments`/`.categories` so tagging-once would actually
  stick - rejected: a bigger, unrelated architectural change. `PAC_CAT`s are designed to
  be re-derived from `identifier` at any time, and existing tests already depend on
  that no-caching behavior; caching risks staleness after direct field mutation. Out of
  scope for this feature.

**Impact:** `Category` needs a new `_issuer: str` `PrivateAttr` (the base PAC-ID's
issuer, cached once when the category is built, alongside the existing
`_segment_bindings`/`_use_position_preserving_segments`) that both
`_get_segments_canonical` and `_get_segments_from_bindings` stamp onto every segment
they construct. For `issuing_system`, the primary category needs a
`{namespace: Category}` lookup, built by `PAC_CAT.categories`'s second pass after
every category exists, that those same rebuild functions consult per-segment by that
segment's own `derivation_namespace` - rather than trying to attach a resolved
`Category` reference directly to a segment instance.

*Investigated 2026-08-05.*

---

## `PAC_ID.__eq__`/`__hash__` scoped to `(issuer, identifier)`, extensions excluded

**Decision:** `PAC_ID` gets a custom `__eq__` (`isinstance(other, PAC_ID) and
self.to_url(include_extensions=False) == other.to_url(include_extensions=False)`) and
`__hash__` (`hash(self.to_url(include_extensions=False))`), replacing pydantic's
inherited default `BaseModel.__eq__`/the `hash(self.to_url())` added 2026-08-03.
Deliberately cross-type: a `PAC_CAT` and a `PAC_ID` with identical issuer+identifier now
compare equal, not just same-type instances. Deliberately compares the *serialized URL
string*, not `self.issuer == other.issuer and self.identifier == other.identifier`
field-by-field - see the dedicated alternative below, this isn't a stylistic choice.

**Why:** `get_non_derived_pac_id()`, `get_parent_pac_id()`, and `derive()`
(`labfreed/pac_id/pac_id.py`) already drop `extensions` when computing identity, with
inline comments stating identity is issuer+identifier - extensions describe "the entity
they're attached to, not its parent." But `__eq__`/`__hash__` never matched that stated
model: pydantic's default `BaseModel.__eq__` compares every field including
`extensions`, and `__hash__` (`hash(self.to_url())`, added in `93f86b6`, undocumented at
the time) defaults to `to_url(include_extensions=True)`. Verified empirically: two
`PAC_ID`s differing only in an extension were `!=` and hashed differently before this
fix, contradicting the derivation methods' own model. Surfaced while checking an
external field-notes brief that assumed (incorrectly, as it turned out) that this was
already the case.

Cross-type equality (`PAC_CAT` vs. `PAC_ID`) is deliberate, not an oversight: `PAC_CAT`
is an interpretive view over `PAC_ID.identifier`, not a different entity, and parsing
already opportunistically upgrades a `PAC_ID` to `PAC_CAT` whenever the identifier is
category-conformant. Treating the two as different identities just because one was
parsed one step further would be an arbitrary distinction the rest of the codebase
doesn't draw.

**Alternatives considered / why not:**

- Add a separate `identity_key()`/`same_identity()` method instead of touching
  `__eq__`/`__hash__`, avoiding a breaking change entirely - rejected: it would leave
  two competing notions of equality on the same class (`==` says "all fields,"
  `identity_key()` says "issuer+identifier"), which is more confusing than a one-time
  breaking fix, especially since the derivation methods already committed the class to
  "identity = issuer+identifier" as a concept.
- Exact-type match (`PAC_CAT(...) != PAC_ID(...)` even with identical issuer+identifier)
  - considered first since it matches pydantic's previous default behavior and avoids
  any behavior change beyond the one being deliberately made, but rejected once
  `PAC_CAT`'s subclass/augmented-view relationship to `PAC_ID` was made explicit (see
  Why above).
- No `PAC_CAT`-specific override - confirmed unnecessary rather than assumed: `PAC_CAT`'s
  `categories`/`main_category`/`processor` computed fields are pure functions of
  `self.identifier` (`labfreed/pac_cat/pac_cat.py`), so inheriting `PAC_ID`'s `__eq__`/
  `__hash__` is automatically correct.
- `self.issuer == other.issuer and self.identifier == other.identifier` (comparing
  `IDSegment` objects directly instead of serialized strings) - built first, then
  rejected: confirmed empirically that `LabFREED_BaseModel._validation_messages`
  (`PrivateAttr(default_factory=list)`, storing `ValidationMessage(source_id=id(self),
  ...)`) participates in pydantic's default equality, so two structurally-identical
  `IDSegment`s that each independently picked up even an *identical* validation message
  compare unequal, because their `source_id`s differ. Real-world `PAC_ID`s almost always
  accumulate at least one validation message during construction (e.g. a
  RECOMMENDATION-level "key not in `WellKnownKeys`"), so this would have silently broken
  `__eq__` for ordinary, valid identifiers - already flagged as an existing landmine in
  `tests/test_PAC_CAT/test_PAC_CAT_main_category_and_processor.py`'s
  `test_main_category_is_the_first_category` docstring, for the same underlying reason.
  Comparing the serialized `to_url()` string instead sidesteps it entirely (strings have
  plain value equality) and, as a bonus, guarantees `__eq__`/`__hash__` consistency by
  construction, since both now derive from literally the same string.

**Impact:** breaking change, released as v1.0.1 (v1.0.0 shipped hours earlier the same
day; accepted given ~zero adoption at the time). Confirmed low internal blast radius
before deciding to fix rather than defer: no internal code compares `PAC_ID` objects by
`==`/uses one as a cache key (the only nearby `lru_cache`,
`pac_id_resolver/resolver.py`, keys on a plain `issuer: str`). Leaves the separate,
already-tracked segment-*ordering* equality gap
([`TODO.md`](TODO.md#structural-category-based-equality-could-sidestep-the-two-parked-exact-layout-stretch-goal-tests))
untouched - that entry is about order-insensitivity within `identifier`, not about
extensions, and shouldn't be conflated with this fix.

*Investigated 2026-08-13, prompted by an external field-notes brief.*

---

## `values_for_key()`'s `Origin` types carry no `describe()`/custom `__eq__` - plain equality and `.model_dump()` already do the job

**Decision:** `PAC_ID.values_for_key(key) -> list[KeyedValue]` (joint lookup across
identifier segments and extensions, extended by `PAC_CAT` for implicit/positional
segment-key resolution) tags each match with a small `Origin` type
(`SegmentOrigin(category_key)`, `ExtensionOrigin(extension_name)`,
`TrexTableOrigin(ExtensionOrigin)` adding `table_key` for a match found inside a T-REX
`TableSegment` column) rather than a flat `source: Literal["segment", "trex"]` string.
These are plain `LabFREED_BaseModel` (pydantic) classes with no methods of their own
beyond their fields.

**Why:** a flat two-value `source` string can't distinguish *which* category a segment
match came from, or *which* named T-REX extension/table a match came from - and the
T-REX spec's own example (`ENV`/`PH`/`CONDUCTIVITY` tables each with a `TEMP` column,
`Specs: T-REX/README.md`) proves this matters: three simultaneous, legitimately
different `TEMP` values inside one T-REX extension would otherwise be indistinguishable.
Extension matching is polymorphic (`ExtensionBase.values_for_key()`, overridden by
`TREX_Extension` to also search table columns) rather than centralized in `PAC_ID`, so
`Origin` needed to be a type hierarchy anyway, one per extension's own internal
structure - a closed `source` enum would have forced every extension type to fit one
shared shape, and blocked adding PAC-ID Attributes as a third source later (see the
parked `PacInfo`-as-RDF-document question in [`TODO.md`](TODO.md#should-pacinfo-become-an-rdfjson-ld-shaped-document)) without
reinventing the concept.

**Alternatives considered / why not:**

- A `describe() -> dict` method on the base `Origin`, overridden per subtype (each
  override merging `super().describe()` with its own extra fields) so generic code
  holding only the base type could still discover subtype-specific detail (e.g.
  `table_key`) without an `isinstance` check - built, then rejected on reflection: it's
  a hand-written reimplementation of pydantic's own `.model_dump()`, which already
  returns every field on the actual runtime instance (subclass-added fields included),
  for free, with no method to write or maintain. The same reasoning covers plain
  printing/logging, not just structured access: verified against the actual class shape
  (`LabFREED_BaseModel` has no `__repr__`/`__str__` override of its own) that
  `repr(TrexTableOrigin(extension_name='SENSORS', table_key='ENV'))` already renders
  `TrexTableOrigin(extension_name='SENSORS', table_key='ENV')` and `str(...)` renders
  `extension_name='SENSORS' table_key='ENV'` - both fields, unprompted - so a caller who
  only prints/logs an `Origin` they're holding as the base type still sees the full
  detail, with nothing to implement.
- A custom `__eq__`/hashing scheme on `Origin` to answer "are these two matches from the
  same place" - unnecessary: pydantic's default equality on these plain model classes
  already checks type *and* fields, so a `TrexTableOrigin` can never spuriously equal a
  plain `ExtensionOrigin` even with overlapping/empty fields, and two origins from
  genuinely the same place compare equal automatically.
- `KeyedValue.value` as a single scalar, with a `row: int` field on `TrexTableOrigin` to
  address a specific table row - rejected: a table *column* key names a set of values
  (one per row), not one row-indexed scalar, so the natural match unit is the whole
  column (`TableSegment.column_data(col)`, already a list). `KeyedValue.value` is
  instead always a list, even for a single scalar match, so callers never branch on
  which kind of match they got before iterating.

*Investigated 2026-08-13, alongside the `values_for_key()` design prompted by the same
external field-notes brief.*

---

## `PAC_CAT.from_categories()` deprecated in favor of named-role construction

**Decision:** `from_categories(issuer, categories: list[Category])` is deprecated
(`DeprecationWarning`, kept functioning, scheduled for removal at v2.0 - see
[`TODO.md`](TODO.md#pending-removals---deprecated-symbols-scheduled-for-v20)) in favor of
`PAC_CAT.from_roles(main: Category, processor: Category | None = None)`, plus a new
companion `Category.from_key(key: str, **fields) -> Category`
(`category_key_to_class_map[key](**fields)`, with the same generic-`Category` fallback
`_cat_from_cat_segments` already uses for an unregistered key). Both new constructors
also get a plain `of` alias (`PAC_CAT.of`, `Category.of`) pointing at the same
implementation, with the docstring on `of` noting `from_roles`/`from_key` as the
encouraged spelling.

**Why:** `from_categories`'s role assignment (which list entry is "main," which is
"processor") is inferred purely from list position, with no validation at all -
`processor`'s own docstring already says "whichever category sits there counts,
regardless of type." That's the same bug class an external field-notes brief described
at the segment-key level (conditionally-assembled positional lists silently getting a
value's meaning wrong), just one level up, at the category-role level. Named parameters
make the wrong assignment structurally impossible instead of merely unvalidated.

Confirmed via tracing `from_categories` → `_resolve_identifier_for_notation` that
`_build_all_categories()` always re-derives `_segment_bindings` fresh from
`self.identifier`, never reusing the caller's original `Category` object - so "build
long-form, force short notation via `to_url(use_short_notation=True)`, re-parse via
`from_url()`" already works correctly on a freshly-constructed `PAC_CAT`, not only on
one parsed from a URL. `from_roles` needed no changes to the underlying re-keying
machinery, only the named-parameter entry point.

**Alternatives considered / why not:**

- Generalize to an arbitrary-length list of roles instead of two named parameters -
  rejected: `PAC_CAT.categories`'s own docstring already documents "capped at these
  two" as a deliberate, spec-level model (a derivation's own issuing system is scoped to
  that one derivation, tracked separately via `derivation_issuing_systems`, not as a
  third top-level slot) - not an arbitrary code limitation needing a more general fix.
- Accept derivation-scoped issuing systems (`+<namespace>` markers) in `from_roles` v1 -
  deferred: materially bigger (constructing the marker structure itself) and a less
  common construction case than main+processor.
- `.of()` as the primary name, matching the field-notes brief's own suggested shape
  (mirroring Java/Kotlin's `List.of()`) - rejected as the *primary* name since every
  existing constructor in this codebase is `from_*` (`from_pac_id`, `from_url`), which
  also names what's being built from; kept as a plain alias instead, since supporting
  both costs nothing and matches habits of callers coming from Java/TS-influenced
  ecosystems.

*Investigated 2026-08-13, prompted by an external field-notes brief.*

---

## T-REX explicit-type wrapper family, and splitting `to_trex()`/`serialize()` into two verbs

**Decision:** `T_REX`'s dict facade (`labfreed/trex/facade/t_rex.py`) gains a family of
explicit-type wrapper classes - `Alphanumeric` (new, forces `T.A`, validates eagerly),
`Text` (new, forces `T.T` - takes *ordinary* text and encodes it to base36 internally at
serialization time), `Numeric`, `Bool`, `Date` (new, completing the set for symmetry,
even though no ambiguity exists for these types today) - so any dict entry's wire type
can be stated explicitly instead of always inferred from the Python value's runtime
type. `Text` is deliberately **not** an alias for the existing `base36` (an earlier
draft of this decision assumed it could be, and was corrected while writing the test for
it): `base36` validates its input as *already* base36-encoded (`re.fullmatch(r'[A-Z0-9]*'
, v)`), so `base36("free text")` raises - it's a pre-encoded-data escape hatch, kept
exactly as-is, not something `Text` could just point at. Separately,
`to_trex()`/`from_trex()` are
renamed to `to_trex_spec()`/`from_trex_spec()` (old names deprecated, kept one version -
see [`TODO.md`](TODO.md#pending-removals---deprecated-symbols-scheduled-for-v20)), and
`T_REX` gains its own `serialize()`/`deserialize(s)`, matching `Spec_T_REX`'s own verb
pair, as the everyday entry point. The five wrapper classes live in
`labfreed/trex/facade/typed_values.py` but are re-exported through
`labfreed/trex/facade/__init__.py` and `labfreed/trex/__init__.py`, matching exactly how
`T_REX`/`DataTable`/`Quantity` are already threaded through both levels - so
`from labfreed.trex import Alphanumeric` works, not just the submodule path.

**Two more pre-existing bugs surfaced while implementing this, both fixed in the same
patch:** (1) `from_trex`/`from_trex_spec` returned a plain `dict`, never actually
`cls(...)`-wrapped into a real `T_REX` instance - latent since dict-like access
(`result['key']`) works identically either way, so nothing caught it until a test
asserted `isinstance(result, T_REX)` directly. (2) Once fixed to properly construct a
`T_REX`, that exposed a second gap: the `T_REX` dict-value union had no `None` member,
even though a T-REX value can legitimately be empty/undefined per spec (and
`to_trex_spec()`'s own dispatch already explicitly handles `v is None`) - confirmed this
was already broken for direct construction too (`T_REX({'X': None})` raised), not just
via `from_trex_spec`; it only went unnoticed because `from_trex`'s un-wrapped dict never
triggered validation. Fixed by adding `None` to the union, matching the pattern
`DataTable.data`'s cell-type union already used.

**Why:** `T_REX.to_trex()`'s type dispatch is ambiguous in exactly one place - a plain
`str` value has to guess between `T.A` and `T.T` via a regex charset check
(`t_rex.py`); every other Python type (`bool`, `Quantity`/numeric, `date`/`time`/
`datetime`) already dispatches unambiguously by `isinstance`. That same string-ambiguity
check was duplicated three times (top-level dict value, `DataTable` column-type
inference, `DataTable` cell-value inference) before this change - now written once and
called from all three sites. `Alphanumeric`/`base36` already existed as one half of an
override (wrapping a string in `base36(...)` already forced `T.T`); this adds the
missing other half (`Alphanumeric` forces `T.A`) and completes the family for symmetry
per explicit decision, rather than adding overrides only where ambiguity happens to
exist today.

The naming split is separate but bundled in the same area: `to_trex()`/`from_trex()`
made sense when the friendly facade class was named `pyTREX` ("this pythonic wrapper,
converted to a trex"); now that the class itself is named `T_REX`, both read as
near-tautological. `to_trex_spec()`/`from_trex_spec()` name what they actually
produce/consume - a `Spec_T_REX` - and become the rarely-touched bridging step (still
needed for e.g. handing a `Spec_T_REX` directly to `TREX_Extension.trex`, which is typed
as `Spec_T_REX`), while `serialize()`/`deserialize()` become the everyday
"dict in/out, wire string out/in" entry point most callers actually want.

**Alternatives considered / why not:**

- Add explicit-type wrappers only for the one case with real ambiguity (`Alphanumeric`
  alongside the existing `base36`) - considered first and initially recommended, but
  rejected in favor of the full family per explicit decision: symmetry (every wire type
  gets an explicit-override option, not just the historically-ambiguous one) was judged
  worth the small amount of extra, unambiguous wrapper classes.
- `Text = base36` (a plain alias) - built first, then rejected once `Text("free text")`
  was actually tried in a test: `base36`'s validator requires already-encoded
  `[A-Z0-9]*` input, so it would reject the exact ordinary-text case `Text` exists for.
  `base36` stays exactly as it was (a distinct, lower-level, pre-encoded-data escape
  hatch); `Text` is a new, separate wrapper.
- `from_str`/`to_str` for the new convenience methods - rejected in favor of
  `serialize()`/`deserialize()`, matching `Spec_T_REX`'s own existing verb pair exactly,
  so a caller learns one vocabulary for "turn this into/from wire text" at both layers
  instead of two different naming schemes for the same operation.

**Related bug found while testing the `Numeric`/`Bool`/`Date` wrappers, same area, same
patch:** `T_REX`'s dict-value type (`Quantity | datetime | time | date | bool | str |
base36 | DataTable`) and `DataTable`'s cell type have no bare `int`/`float` member.
Pydantic's "smart" union mode only prefers an exact-type match over a coercion when an
exact match exists among the union's members - since none did, a plain `int`/`float`
was silently coerced into a `datetime` via Unix-timestamp interpretation (`T_REX({"X":
5})["X"]` was `datetime(1970, 1, 1, 0, 0, 5)`), before `to_trex()`'s own, correctly-
ordered `isinstance(v, (int, float))` check (checked *before* the `datetime` check
there) ever got a chance to see the original value - confirmed in isolation with a bare
`pydantic.TypeAdapter` on just the union type, no `T_REX` code involved. Fix: add
`int | float` to both unions - verified this alone makes pydantic's smart-mode matching
pick the exact type immediately for the previously-coerced case, without disturbing the
already-correct ones (`bool`, `Quantity`).

*Investigated 2026-08-13, prompted by an external field-notes brief.*

---

## `_evaluate_jsonpath()` deep-copies its input - `jsonpath_ng.ext`'s `find()` mutates in place for some expressions

**Decision:** `ResolverConfigEvaluator._evaluate_jsonpath()` now calls
`jsonpath_expr.find(copy.deepcopy(pac_id_json))` instead of `jsonpath_expr.find(pac_id_json)`.

**Why:** confirmed, in complete isolation with no LabFREED code involved, that
`jsonpath_ng.ext`'s `find()` mutates its input dict in place for a recursive-descent
wildcard combined with a filter predicate (`$..*[?(@.key == 'X')].value` - exactly the
pattern `cit.yaml`'s `Manual`/`CoA` macro templates use): a plain dict at the query root
gets silently replaced by a nested list. `ResolverConfigEvaluator.evaluate()` builds one
`pac_id_json` dict and reuses it across every block's `applicable_if` condition and every
entry's `template_url` within a single call - so the first block whose template uses this
pattern silently corrupted every block evaluated after it, since `$.pac.issuer` and similar
conditions no longer resolved against the corrupted structure. This was already present,
unchanged, in the actual tagged/pushed `v1.0.0` release (confirmed via `git merge-base`) -
not a regression from anything in this session; found while investigating why
`tests/test_resolver/test_resolver_config_sanity_check.py`'s `cit.yaml`-based tests
(`test_cit_yaml_device_gets_shop_and_manual_and_logic_showcase_entries`,
`test_cit_yaml_consumable_also_gets_coa`) were failing despite testing unrelated work.

**Alternatives considered / why not:**

- Rewrite `cit.yaml`'s macros to avoid the `$..*[?(...)]` pattern - rejected: that's valid,
  useful JSONPath syntax; papering over a library bug by telling users to avoid a whole
  class of otherwise-correct expressions isn't a real fix, and doesn't protect against the
  same `jsonpath_ng` behavior showing up via some other expression shape later.
- Copy `pac_id_json` once per `evaluate()` call instead of once per `_evaluate_jsonpath()`
  call - rejected: still vulnerable to corruption *within* a single block, where a
  condition and multiple `template_url` placeholders can each independently call
  `_evaluate_jsonpath()` against what would still be one shared, mutable dict.
- Pin `jsonpath-ng` to a version without this behavior - not pursued: `pyproject.toml`
  already has an open-ended `jsonpath-ng>=1.7.0` (installed here: `1.8.0`), and pinning
  would only mask the underlying assumption that a read-only-looking library call is safe
  to call repeatedly against shared mutable state. The defensive copy protects against this
  regardless of which version resolves.

*Investigated and fixed 2026-08-14.*

---

## `Werkzeug` promoted to a base dependency; `Flask` itself stays `extended`/`experimental`-only

**Decision:** `Werkzeug>=3.1.0` added to `pyproject.toml`'s base `dependencies`, alongside
the existing `extended`/`experimental` extras that already carry `Flask` (which itself
depends on Werkzeug transitively).

**Why:** found via a GitHub Actions CI failure - `pytest`'s collection step crashed with
`ModuleNotFoundError: No module named 'werkzeug'` on a runner that had only installed
`pip install .[dev]`. Root-caused with a local import-blocking simulation (no actual
uninstall needed): a bare `import labfreed`, with *no extras at all*, already reaches
`werkzeug` - `labfreed/pac_attributes/__init__.py` (imported unconditionally by
`labfreed/__init__.py`) directly imports `AttributeServerRequestHandler` from
`server/server.py`, which imports `werkzeug.datastructures.accept.LanguageAccept` at
module level; `api_data_models/request.py` (also unconditionally imported) uses
`werkzeug.http.parse_accept_header` the same way, to parse/construct/serialize
`Accept-Language` header values (`_find_response_language`'s `.best_match()` call,
`AttributeRequestData`'s `language_preferences` field). Neither of these modules imports
`flask` itself anywhere - confirmed by grep. This means **any** `pip install labfreed`
user, not just this CI runner, would have hit the same crash on the most basic possible
action (`import labfreed`), since `Werkzeug` was previously reachable only as a
transitive dependency of `Flask`, which is itself gated behind the `extended`/
`experimental` extras.

**Alternatives considered:**

- Add `Flask` itself to base dependencies - rejected: nothing in the base import chain
  actually runs a Flask app (no `import flask` anywhere reachable without an extra); that
  would drag the full web-framework dependency tree (`blinker`, `click`, `itsdangerous`,
  `jinja2`, `markupsafe`, ...) into every install, including someone using only bare
  PAC-ID/PAC-CAT/T-REX, for the sake of one HTTP-header-parsing utility.
- Reimplement `Accept-Language` parsing/negotiation without Werkzeug (a small,
  self-contained RFC 7231 q-value parser) - considered, but rejected as unnecessary
  scope for this fix: `werkzeug.http.parse_accept_header`/`LanguageAccept` are
  well-tested, and the actual bug is a packaging/extras-classification mistake, not a
  reason to drop the dependency entirely. Revisit only if `Werkzeug` itself ever becomes
  undesirable as a base dependency for an unrelated reason.
- Make the `werkzeug` imports lazy (import inside the functions that use it, not at
  module level) instead of promoting it to a base dependency - rejected: the request
  handler's `Accept-Language` negotiation and the request/response data models'
  `language_preferences` field are core, always-available functionality (exported at the
  top-level `labfreed.*` namespace, no extra required to reach them per
  `pac_attributes/__init__.py`'s `__all__`) - deferring the `ImportError` to first-use
  would just move the same crash from import-time to request-time for every bare-install
  user who actually exercises language negotiation, instead of fixing the real
  classification problem.

**Impact:** also fixed `.github/workflows/pypi-publish.yml`'s own `pip install .[dev]`
step to `pip install .[dev,extended]` - even with the dependency fix above,
`extended`-only tests (Flask blueprint factory, Excel data source) still need that extra
installed to collect at all; confirmed `dev,extended` is sufficient for a full green run
(`experimental`/`units` are not needed for collection). Both fixes verified against a
clean venv reproducing CI's exact install command, not just the shared devcontainer
environment (which already had every extra installed, masking this).

*Investigated 2026-08-13, while diagnosing a GitHub Actions test failure during the
1.0.0 release.*

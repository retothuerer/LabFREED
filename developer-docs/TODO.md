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

---

## Add a PAC-ID conversion stub for non-PAC-ID scanned identifiers

Not every scanned/typed identifier is a valid PAC-ID (e.g. Carl Roth's own internal
format, `roth503341590!7029.2!1!` — no PAC-ID has been issued for it, see
`CARL_ROTH_HAS_PAC_ID` in
`labfreed-webtools/instrument_demo/bp_instrument_demo.py`). Neither `PAC_ID.from_url()`
nor `AttributeClient.get_attributes()` has a path for this today —
`PAC_Parser._parse_pac_id` (`labfreed/pac_id/url_parser.py`) raises unconditionally when
the string doesn't match the `issuer/identifier` pattern, regardless of
`suppress_validation_errors` (that flag only gates the later `is_valid` check, not the
regex-mismatch raise).

There's no LabFREED spec yet for "convert an arbitrary scanned string into a PAC-ID," so
for now this can be a thin stub that just proxies to the Apini cloud attribute service's
undocumented `/pac-id/<raw string>` endpoint in the background (GET, falling back to a
POST with a `{"input": ...}` body on 404/405 — see
`labfreed-webtools/scripts/test_apini_attribute_api.py` for the reference calls this
would mirror). Revisit once/if a real conversion mechanism gets specified.

Auth still needs to be sorted out before this leaves stub status: the existing
`ATTRIBUTE_SERVER_AUTH` / `PatternMatchedAuth` credential wiring in
`bp_instrument_demo.py` covers the `/attributes` endpoint on that same deployment;
confirm whether `/pac-id` expects the same header/key or something else.

---

## ~~Clarify whether a trailing (or double) `/` in an `identifier` is spec-legal~~ (resolved)

Resolved, revised 2026-07-29: a *doubled* (or inner) `/` still produces a genuinely
empty `id segment` and stays an ERROR - see ["Empty `id segment`s (trailing/double `/`)
are rejected, not
normalized"](design-choices.md#empty-id-segments-trailingdouble--are-rejected-not-normalized)
for the reasoning. A single *trailing* `/`, however, is now tolerated: `PAC_Parser`
strips it before splitting into segments (so it contributes no segment at all) and
flags it with a WARNING instead. The PAC-ID spec wording was updated to match: `id
segment` "MUST contain at least one character", and the URL-format `path` row now
states a trailing `/` "MUST NOT be considered part of the identifier". A stray
trailing `/` found in the PAC-CAT spec's own example table was fixed alongside the
original (double-`/`) decision.

Still open: `bp_instrument_demo.py` still strips the trailing `/` itself before calling
`PAC_ID.from_url()` (see `rstrip('/')` in the PAC-Ninja conversion path) - this is now
redundant for a single trailing `/` (the library does it), but callers building
`identifier` strings from external input still need to guard against a *doubled*/inner
`/` themselves, since the library will not silently fix that up for them.

---

## Every `dev` version bump needs a deliberate `labfreed-webtools` requirements.txt bump

`labfreed-webtools/requirements.txt` pinned `labfreed[extended]` with an open-ended
floor (`>=1.0.0b44`, no upper bound) while `dev` is only a release away from PyPI -
meaning any future pre-release cut from `dev` could reach the deployed landing page on
its next redeploy with zero gate. Tightened to an exact pin (`==1.0.0b44`) on
2026-07-28 as part of the [[project_labfreed_pac_attributes_improvement_plan]] Phase 0
work, but that only freezes the *current* risk - it doesn't stop it recurring.

This is a process gap, not a one-time fix: whoever next bumps `labfreed/__init__.py`'s
`__version__` and cuts a PyPI release should also deliberately review and bump this
exact-pin line in `labfreed-webtools/requirements.txt`, rather than leaving it stale
(which is safe but eventually blocks a legitimate upgrade) or reverting to an
open floor (which reintroduces the original risk). Consider whether the `release`
skill should gain a step for this once labfreed-webtools' own repo conventions are
better established here.

**Revised 2026-07-29:** deliberately reopened to a floor, `labfreed[extended]>=1.0.0`,
in preparation for the real `1.0.0` release that will land once the current major
refactor (units/UCUM work, PAC-ID Attributes cleanup, etc.) is done. This isn't the same
risk as the original open floor: pip excludes pre-releases from an unqualified `>=`
range, so `>=1.0.0` cannot resolve to any `1.0.0bNN` pre-release - only the real final
`1.0.0` (or later) satisfies it. Concretely, this means `pip install -r requirements.txt`
will **fail to resolve at all** (no matching distribution) until `1.0.0` is actually
published to PyPI - a hard stop, not a silent stale-version fallback, so it's safe to
leave in place across the rest of the refactor. Once `1.0.0` ships this floor will
resolve automatically with no manual bump needed - but it still has no upper bound, so
the original "silently jumps into a future version with zero gate" risk returns for any
`1.1.0`/`2.0.0` released afterward. Revisit then: an upper bound (e.g. `<2.0.0`) would
close that gap without reintroducing the manual-bump toil this revision was meant to
avoid.

---

## Pull the shared "canonicalize, then fall back to raw string" lookup out of the data sources

`Dict_DataSource.attributes()` (`server/attribute_data_sources.py`) and
`_BaseExcelAttributeDataSource.attributes()` (`pythonic/excel_attribute_data_source.py`)
both do the same sequence: try `PAC_CAT.from_url(subject_id, suppress_validation_errors=True)`,
canonicalize via `.to_url(...)` if valid, look up by the canonical key, and fall back to
the raw, as-given `subject_id` if that misses - see design-choices.md, "Empty id
segments... revision 2026-07-29" for why the fallback exists (a tolerated trailing `/`
canonicalizes differently from a raw stored key). Currently duplicated near-verbatim in
both places. Worth extracting into one shared helper (e.g. a small function or mixin
both data sources call) so the fallback logic - and any future fix to it - only has to
exist once. Not done as part of the Phase 2 fixes that introduced this duplication,
since it's a pure refactor with no behavior change; flagged for a later pass.

---

## `app_infrastructure.py` has a dead, second copy of the service-availability logic

Found while extracting `service_availability.py` from `services.py` (see
[`design-choices.md`](design-choices.md#service-availability-network-checks-split-out-of-servicegroupservice-with-no-shim)).
`labfreed/labfreed_extended/app/app_infrastructure.py` has its own near-duplicate of the
same HTTP-checking logic:

- `update_user_handover_states()` (lines 88-96) - a second `ThreadPoolExecutor` +
  connectivity-guard implementation, confirmed via grep to be called nowhere in either
  `LabFREED` or `labfreed-webtools`.
- Its own separate module-local `_has_internet_connection()` (lines 98-103) - uses
  `requests.head` where `services.py`'s version used `requests.get`, a second,
  inconsistent copy of the same check.
- Line 54's `(sg.update_states() for sg in service_groups)` is a bare, never-iterated
  generator expression - also dead (already flagged in
  [[project_labfreed_pac_attributes_improvement_plan]] Phase 4).

Left untouched since this lives entirely in the `pac_issuer_lib`/issuer-app area
deferred to its own branch. When that phase happens: delete the dead
`update_user_handover_states`/`_has_internet_connection` pair, and if the
never-iterated generator turns out to need reviving, point it at
`service_availability.check_service_group` instead of re-implementing this a third time.

---

## `client/auth.py` shipped to PyPI with no `CHANGELOG.md` entry

`AuthRule`/`PatternMatchedAuth`/`env_credential` (`labfreed/pac_attributes/client/auth.py`)
are already live in production PyPI builds past `1.0.0b44` - confirmed by grep, the
module exists and is imported directly by `labfreed-webtools` (`bp_instrument_demo.py`,
`bp_attribute_server.py`) - but `CHANGELOG.md` has zero mentions of authentication.
A process gap found while auditing the client/server area during
[[project_labfreed_pac_attributes_improvement_plan]] Phase 3, unrelated to that plan's
actual fixes. Add a retroactive `CHANGELOG.md` entry under the pending `v1.0.0` heading
(new public API, not breaking) so the release history isn't silently missing a real
feature.

---

## Fill in `ucum_for_unece_code`'s normalization gaps as they're actually hit

Related to: ["Automatic, optional UNECE<->UCUM unit mapping via pint/ucumvert"](design-choices.md#automatic-optional-unecucum-unit-mapping-via-pintucumvert)

`ucum_for_unece_code` (`labfreed/well_known_keys/unece/ucum_bridge.py`) derives a UCUM string for
a UNECE Common Code by normalizing UNECE's own `symbol` field (superscript digits, `µ`->`u`,
`°C`->`Cel`, `·`->`.`). That covers 877/1511 active UNECE entries with a symbol; the rest -
almost entirely imperial/trade units (`oz/ft²`, `BtuIT/h`, `ppm`, `kbyte`, ...) - raise
`UcumSupportError` instead of returning a guess, by design (see the linked design-choice entry -
curating all ~2159 codes upfront was explicitly what this change avoided).

If a real T-REX payload ever uses one of these codes and hits the error, add that specific code's
UCUM translation to `_normalize_unece_symbol` (or a small lookup table next to it) at that point,
rather than trying to pre-empt the whole remaining set now.

---

## Structural (category-based) equality could sidestep the two parked "exact layout" stretch-goal tests

Related to: ["Convenience API for PAC-ID/PAC-CAT derivation
namespaces"](#convenience-api-for-pac-idpac-cat-derivation-namespaces) (same test file)

`tests/test_PAC_CAT/test_PAC_CAT_derivation_namespace.py`'s two `@pytest.mark.skip(reason="NOT
REVIEWED")` stretch-goal tests
(`test_forced_long_notation_preserves_exact_layout_across_categories`,
`test_chained_derivation_namespaces_stay_in_original_order`) both assert equality on the
*serialized URL string* - `pac.to_url(use_short_notation=False) == url_in` - which demands
`to_url()` reproduce the exact original segment ordering byte-for-byte, not just an equivalent
structure. Raised while looking at these tests: comparing the *parsed* structure instead (e.g. a
`PAC_CAT`/`Category`-level equality or a segment-set comparison, so two PAC-CATs are equal
whenever their categories/segments carry the same key-value pairs regardless of on-the-wire
ordering) would let both tests express what they actually care about - "did the data survive a
round trip" - without also requiring literal layout preservation.

Not scoped or acted on: `PAC_ID`/`PAC_CAT` have no `__eq__` today (confirmed by grep - the only
two `__eq__` overrides in the package are in `pac_id_resolver/resolver_config.py` and
`cit_v1.py`, unrelated), so this would be new API, not a fix to something broken. Bigger than the
two tests above suggest: a grep across `tests/` shows roughly 43 uses of the
`.to_url() == <literal>` / `to_url(use_short_notation=...)` pattern spanning at least
`test_PAC_CAT_derivation_namespace.py`, `test_PAC_CAT_parse_serialize_sequence.py`,
`test_PAC_CAT_serialize.py`, `test_PAC_ID_serialize.py`, `test_pac_id_parse.py`,
`test_excel_attribute_data_source.py`, `test__serialize.py`, `test_sanity_check.py`, and the
generated-tests suite - each would need individually judging whether it's actually testing
serialization fidelity (should keep comparing URL strings) or just object identity/round-trip
(could switch to structural equality once it exists). Revisit alongside the derivation-namespace
convenience-API pass above, since both touch the same test file and category model.

---

## Convenience API for PAC-ID/PAC-CAT derivation namespaces

Related to the derivation-namespace (`+<namespace>`) support in `pac_id.py`/`pac_cat.py`
(see `tests/test_PAC_CAT/test_PAC_CAT_derivation_namespace.py` - as of 2026-07-29, 11 of
its 14 tests still carry `@pytest.mark.skip(reason="NOT REVIEWED")`, though all 14 pass
once unskipped; implementation looks functionally complete, review of those tests is
what's actually outstanding).

Requested convenience methods, with current status:

- **list all namespaces** - already exists: `PAC_ID.get_derivation_namespaces()`.
- **is derived** - already exists: `PAC_ID.has_derivation_segments()`.
- **parent** - now exists: `PAC_ID.get_parent_pac_id()`, one level up (unlike
  `get_non_derived_pac_id()`, which strips back to the root). As of 2026-07-30 it also
  covers marker-less (issuer self-derivation) parents, not just `+<namespace>`-marked
  ones - see design-choices.md
  "[`PAC_ID.get_parent_pac_id()` covers issuer self-derivation too, not just `+<namespace>`-marked derivation](design-choices.md#pac_idget_parent_pac_id-covers-issuer-self-derivation-too-not-just-namespace-marked-derivation)".
  `is_derived_from`'s ancestor walk still only follows the marker-based chain, not the
  no-marker one - left as a follow-up there, not scoped yet.
- **derive from** - now exists: `PAC_ID.derive(namespace, *segments)`.

Other candidates worth considering once this gets picked up:

- `segments_by(namespace)` (or a `Category` method) to filter `.segments` down to what
  one namespace contributed - `CategorySegment.derivation_namespace` already tags each
  segment, but there's no filter helper for "everything ACMELABS.COM added."
- `derivation_chain()` - the full lineage as an ordered list of
  `(namespace, segments_added)`, rather than just the namespace names
  (`get_derivation_namespaces`) or just the root (`get_non_derived_pac_id`).
- Domain-shape validation on `<namespace>` itself - `PAC_ID._validate_issuer` already
  checks that the top-level `issuer` looks like a real domain name; the `+<namespace>`
  marker's value gets no equivalent check today, only generic `IDSegment` character rules.
- Plain (non-`PAC_CAT`) `PAC_ID`s have no per-segment `derivation_namespace` tag -
  `CategorySegment` only exists inside `PAC_CAT`. Worth deciding whether that tagging
  should move up to `IDSegment` itself so it's available without going through `PAC_CAT`.

Not scoped yet - revisit once the currently-parked derivation-namespace tests are
reviewed and unskipped.

---

## Real UCUM unit conversion for `SignalsActionConsumer.update_amount`

Related to: ["Well-known action handler: `action-generic` params travel as plain
query params, not through the CIT
template"](design-choices.md#well-known-action-handler-action-generic-params-travel-as-plain-query-params-not-through-the-cit-template)

`SignalsActionConsumer.update_amount` (`labfreed_experimental/actions/consumers/signals_consumer.py`)
only accepts a small hardcoded whitelist of volume units (`mL`, `L`, `l`, `uL`) and
converts to mL by a fixed factor - it does not do general UCUM unit conversion (e.g.
mass units, or arbitrary volume units/prefixes). General conversion is a large enough
topic (dimensional analysis, which unit the target system's own field actually expects)
to deliberately skip for now rather than build ad hoc alongside the action handler.
`labfreed.utilities.quantity.Quantity`/`well_known_keys.unece.ucum_bridge` already wrap
`pint`/`ucumvert` and could plausibly back a real implementation later.

Not scoped yet - revisit once there's a concrete second unit (or second consumer) that
needs it.

---

## ~~Other plain-`Enum` classes that could become `StrEnum`~~ (converted, see below)

Related to: ["Attribute-key enums migrated from `Enum` to
`StrEnum`"](design-choices.md#attribute-key-enums-migrated-from-enum-to-strenum)

Surveyed every `Enum` subclass in the codebase for the same `.value`-boilerplate /
silent-equality-miss issue that motivated converting the attribute-key enums. All four
candidates found were converted to `StrEnum` on 2026-07-31, with their `.value`
call sites simplified to match:

- **`ServiceType`** (`labfreed/pac_id_resolver/resolver_config_common.py`) - converted.
  `resolver_config_common.py`'s `_validate_service_type` and
  `resolver_config.py`'s `ResolverConfigEntry._validate_service_type` both dropped
  their `isinstance(..., ServiceType)`/`.value` unwrapping dance, now comparing
  `ServiceType` members directly. The `ServiceType | str`/`ServiceType|str` type hints
  on `CITEntry_v1.service_type`/`ResolverConfigEntry.service_type` were left as-is
  (not part of this change) - confirmed empirically that pydantic's `Enum | str`
  union resolves a plain string input to `str`, not the enum, regardless of `Enum` vs
  `StrEnum`, so `cit_v1.py:190`'s `e.service_type.value` remains a **pre-existing,
  separate latent bug**: it will raise `AttributeError` if `service_type` was parsed
  from CIT text (a plain `str`) rather than constructed with the enum member directly.
  Not fixed here - out of scope for this change, flagged for awareness.
- **`WellKnownKeys`** (`labfreed/well_known_keys/labfreed/well_known_keys.py`) -
  converted. `id_segment.py:68` simplified from
  `key not in [k.value for k in WellKnownKeys]` to `key not in WellKnownKeys`
  (verified `in` against a `StrEnum` class checks member values on this Python
  version, 3.14).
- **`GS1ApplicationIdentifier`** (`labfreed/well_known_keys/gs1/gs1_ai_enum_sorted.py`)
  - converted. Still has zero references outside its own definition file.
- **`ServiceUUID`/`PAC_Characteristics`** (`labfreed/labfreed_experimental/pac_disco/ble_uuid.py`)
  - converted. `ServiceUUID.all_uuid()` simplified from `member.value.lower()` to
    `member.lower()`; `ble_central.py`'s `client.read_gatt_char(characteristic.value)`
    simplified to `client.read_gatt_char(characteristic)`.

Update 2026-07-31: converted all four anyway, at the user's request ("nothing speaks
against it and it reduces the `.value` error surface") - see
[[developer-docs/design-choices.md]]'s "`auto()`-backed enums (`ServiceStatus`,
`ValidationMsgLevel`) also converted to `StrEnum`, with new explicit string values"
entry for the full reasoning, especially the distinction that `ServiceStatus`/
`ValidationMsgLevel` needed new explicit string values (previously `auto()`-int-backed)
rather than just a base-class swap:
- **`ServiceStatus`** (`labfreed/pac_id_resolver/services.py`) - `auto()` ints replaced
  with `"active"`/`"inactive"`/`"unknown"`.
- **`ValidationMsgLevel`** (`labfreed/labfreed_infrastructure.py`) - `auto()` ints
  replaced with `"error"`/`"warning"`/`"recommendation"`/`"info"`.
- **`Webframework`** (`attribute_server_factory.py`) - base-class swap only, values
  unchanged (`"flask"`/`"fastapi"`).
- **`Direction`** (`labfreed/qr/generate_qr.py`) - `class Direction(str, Enum)` ->
  `class Direction(StrEnum)`, cosmetic modernization only, no behavior change.

## Change Log

### v1.0.0
PAC-ID
- supporting PAC.LI issuer
- BREAKING: `WellKnownKeys` and `GS1ApplicationIdentifier` now derive from `StrEnum` instead of `Enum` (same treatment as the PAC-ID Attributes key enums below); `id_segment.py`'s well-known-key check simplified accordingly, no `.value` needed

PAC-CAT
- added new categories 
- BREAKING: Renamed category MM to MX

PAC-ID Resolver
- Transition to improved resolver configuration ( replaces coupling information table )
- BREAKING: `ServiceType` now derives from `StrEnum` instead of `Enum`; `_validate_service_type` in both `resolver_config_common.py` and `resolver_config.py` dropped their manual `.value`/`isinstance` unwrapping now that members compare directly against plain strings
- BREAKING: `ServiceStatus` (`Service.status`) now derives from `StrEnum` with explicit string values (`"active"`/`"inactive"`/`"unknown"`) instead of plain `Enum` with `auto()`-generated int values; any code reading `.value` directly (none found in this codebase) would now get a string instead of an int
- new optional `key` field on `ResolverConfigEntry`/`Service`: an absolute IRI, drawn from the same shared vocabularies PAC-ID Attributes already sources its own `key` from, identifying what an entry semantically *is* (e.g. "this is a Material Safety Data Sheet"), orthogonal to `application_intents` (which identifies which use case selects it). `PacInfo` gained matching `get_user_handover(s)_by_key()`/`get_action(s)_by_key()` lookups


PAC-ID Attributes
- new building block
- BREAKING: renamed PhysoChemicalProperties to PhysicoChemicalProperties (typo fix; deprecated alias kept for one more major version)
- BREAKING: fixed MELTINGPOINT value typo (meltinggpoint -> meltingpoint) - still an unreleased `.../dummy/...` placeholder key, fixed before real adoption
- BREAKING: replaced BOILINGPOINT, MELTINGPOINT and DENSITY `.../dummy/...` placeholder values with real qudt.org quantitykind URIs, matching what a real attribute server (Apini) returns - still unreleased placeholder keys, fixed before real adoption
- added well-known attribute keys MOLARMASS and FLASHPOINT to PhysicoChemicalProperties, and new ChemicalIdentifiers (CAS_NUMBER, EC_NUMBER, EMPIRICAL_FORMULA), GuaranteeAnalysisProperties (ASSAY, WATER_CONTENT) and DocumentKeys (DATASHEET, SAFETY_DATA_SHEET) enums, sourced from a real Apini attribute server response for a Carl Roth solvent
- renamed well_knonw_attribute_keys module to well_known_attribute_keys (typo fix; deprecated shim module kept for one more major version)
- BREAKING: `Webframework` (`AttributeServerFactory`) now derives from `StrEnum` instead of `Enum`, for consistency; no known call site read `.value` on it before
- BREAKING: attribute key enums (MetaAttributeKeys, IdentifierKeys, PhysicoChemicalProperties, etc.) now derive from `StrEnum` instead of `Enum`, matching `CommonQuantityUnit`; members are usable directly wherever a `str` is expected (dict keys, equality checks, `pyAttribute(key=...)`) without `.value` - existing `.value` call sites are unaffected, but code relying on `isinstance(key, str)` being `False` or on the old `str(key)` repr-style output will observe different behavior
- NumericAttributeItemsElement's unit validation now shares the same UCUM check used across the package (authoritative when the new optional `units` extra is installed), instead of its own separate regex


General
- Minor Bugfixes
- `labfreed_experimental.pac_disco`'s `ServiceUUID`/`PAC_Characteristics` now derive from `StrEnum` instead of `Enum` (no compatibility guarantee on this module, not tagged BREAKING)
- `qr.generate_qr`'s `Direction` modernized from `class Direction(str, Enum)` to `class Direction(StrEnum)` - purely cosmetic, identical runtime behavior
- BREAKING: `ValidationMsgLevel` (used across every building block's validation messages) now derives from `StrEnum` with explicit string values (`"error"`/`"warning"`/`"recommendation"`/`"info"`) instead of plain `Enum` with `auto()`-generated int values; `ValidationMessage.level` would now serialize as a string via `model_dump()`/`model_dump_json()` instead of an int if ever dumped directly (it's stored in a private attribute and excluded from the parent model's own serialization by default, but is a public field on `ValidationMessage` itself) - no in-repo call site read `.value` on it before this change
- BREAKING: reorganization of module structure > some import paths have changed
- BREAKING: renamed Quantity.float property to Quantity.as_float (the name collided with the float type used in Quantity's own annotations, breaking model construction on Python 3.14)
- moved `Quantity` from `labfreed.trex.pythonic.quantity` to `labfreed.utilities.quantity` (it's used by PAC-ID Attributes too, not only T-REX); `from labfreed.trex.pythonic import Quantity` still works, but the old submodule path is gone - `unece_unit_code_from_quantity` (T-REX-specific) moved into `pyTREX.py`
- new optional `units` extra (`pip install labfreed[units]`, adds pint+ucumvert): Quantity<->T-REX UNECE unit-code mapping is now automatic for compound/non-SI units (mol/L, kg/m3, Cel, ...) instead of only working when a unit's UNECE symbol happened to equal its UCUM string
- BREAKING (edge case): when a unit can't be resolved to a UNECE code and the `units` extra isn't installed, `Quantity`/`pyTREX.to_trex()` now raise `UcumSupportError` (an `ImportError` subclass) instead of `ValueError` - only observable if calling code specifically caught `ValueError` from this path, which previously fired for every non-exact-match unit
- BREAKING: `Quantity` now validates that `unit` is a valid UCUM unit at construction time (structure only without the `units` extra, full symbol-level check with it) and raises `ValueError` otherwise - previously any string was accepted. Pass `dont_enforce_ucum_units=True` to the constructor to bypass this (discouraged)
- `Quantity.__str__` pretty-prints its unit (e.g. `kg/m3` -> `kg/m³`) when the `units` extra is installed, instead of the old naive `.`->`·` substitution



### v0.2.12
- bugfix:no warning message if PAC-CAT has same segment key in two segments

### v0.2.11
- bugfix:added missing well known segment key '250'
  
### v0.2.10
- bugfix:added missing well known segment key '20'
  
### v0.2.9
- bugfix in serialization of PAC-CAT with multiple categories
  
### v0.2.8
- option to pass cache to resolver for speedier check of service availability

### v0.2.7
- Improved README. No functional changes
  
### v0.2.6
- PAC_ID.to_url() preserves the identifier as is by default but allows to force short or long notation.
- PAC-ID Resolver does not try to resolve PAC-CAT with CIT v1.
  
### v0.2.5
- resolvers checks service states by default
- improvements and bugfixes in conversion from python types to TREX
- follow better naming conventions in CIT v1 
  
### v0.2.4
- improvements in formatting of validation messages
- bugfix in DataTable
 
### v0.2.3
- improvements in formatting of validation messages
- bugfix in DisplayNameExtension
  
### v0.2.2
- minor changes for better access of subfunctions. No change in existing API
  
### v0.2.1
- improved docu. no code changes

### v0.2.0b2
- improvements in api consistency and ease of use
- restructured code for better separation of concerns
- support for coupling information table v1

### v0.1.1
- minor internal improvements and bugfixes
  
### v0.1.0
- DRAFT Support for PAC-ID Resolver

### v0.0.20
- bugfix in TREX table to dict conversion
- markdown compatible validation printing 

### v0.0.19
- supports PAC-ID, PAC-CAT, TREX and DisplayName
- QR generation 
- ok-ish test coverage




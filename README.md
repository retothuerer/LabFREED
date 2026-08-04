# LabFREED for Python

[![PyPI](https://img.shields.io/pypi/v/labfreed.svg)](https://pypi.org/project/labfreed/) ![Python Version](https://img.shields.io/pypi/pyversions/labfreed) [![Test Labfreed](https://github.com/retothuerer/LabFREED/actions/workflows/run-tests.yml/badge.svg)](https://github.com/retothuerer/LabFREED/actions/workflows/run-tests.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/retothuerer/LabFREED/blob/main/LICENSE) [![Ruff](https://img.shields.io/badge/style-Ruff-black?logo=ruff&labelColor=gray)](https://github.com/astral-sh/ruff)

This is a Python implementation of [LabFREED](https://labfreed.org/) building blocks.

LabFREED itself is an open, vendor-neutral community initiative for pragmatic lab
digitalization, contributed to mainly by [ApiniLabs](https://github.com/ApiniLabs),
[Buchi](https://www.buchi.com), and [wega](https://www.wega-it.com), with 40+ supporting vendors/adopters. See
[labfreed.org](https://labfreed.org/) for the building-block specs themselves, or join
the community [Discord](https://discord.com/invite/bxAghUAHFE) for questions and
discussion. This repo is only the Python reference implementation.

## Contents

- [LabFREED for Python](#labfreed-for-python)
  - [Contents](#contents)
  - [Supported Building Blocks](#supported-building-blocks)
  - [Installation](#installation)
  - [Using with Claude Code](#using-with-claude-code)
  - [Package Structure](#package-structure)
  - [Design Philosophy](#design-philosophy)
  - [Usage Examples](#usage-examples)
    - [Parse a simple PAC-ID](#parse-a-simple-pac-id)
    - [Show recommendations:](#show-recommendations)
    - [Save as QR Code](#save-as-qr-code)
    - [PAC-CAT](#pac-cat)
    - [Parse a PAC-ID with extensions](#parse-a-pac-id-with-extensions)
      - [Display Name](#display-name)
      - [TREX](#trex)
    - [Create a PAC-ID with Extensions](#create-a-pac-id-with-extensions)
      - [Create PAC-ID](#create-pac-id)
      - [Create a TREX](#create-a-trex)
      - [Combine PAC-ID and TREX and serialize](#combine-pac-id-and-trex-and-serialize)
  - [PAC-ID Resolver](#pac-id-resolver)
  - [PAC-ID Attributes](#pac-id-attributes)
  - [Versioning](#versioning)
  - [Change Log](#change-log)
    - [v1.0.0](#v100)
    - [v0.2.12](#v0212)
    - [v0.2.11](#v0211)
    - [v0.2.10](#v0210)
    - [v0.2.9](#v029)
    - [v0.2.8](#v028)
    - [v0.2.7](#v027)
    - [v0.2.6](#v026)
    - [v0.2.5](#v025)
    - [v0.2.4](#v024)
    - [v0.2.3](#v023)
    - [v0.2.2](#v022)
    - [v0.2.1](#v021)
    - [v0.2.0b2](#v020b2)
    - [v0.1.1](#v011)
    - [v0.1.0](#v010)
    - [v0.0.20](#v0020)
    - [v0.0.19](#v0019)
  - [Getting Help / FAQ](#getting-help--faq)
  - [Contributing](#contributing)
- [Attributions](#attributions)

## Supported Building Blocks
- PAC-ID
  - Parsing
  - Serialization
- PAC-CAT
  - Interpretation of PAC-ID as categories
- T-REX
  - Parsing 
  - Serialization
- Display Extension
  - base36 <> str conversions
- PAC-ID Resolver
  - support for resolver configuration v2 (improved version)
  - use of multiple resolver configuration
- PAC-ID Attributes
  - client and server code
- Generation of QR codes (PAC-ID with extensions)
  
- Validation (with Errors Recommendations)

## Installation
You can install LabFREED from [PyPI](https://pypi.org/project/labfreed/) using pip:

```bash
pip install labfreed
```

Some parts of the package need extra dependencies that are not installed by default — see [Package Structure](#package-structure) below.

## Using with Claude Code

If you're writing Python against this package with [Claude Code](https://claude.com/claude-code), install the bundled skill so Claude already knows the building blocks and has working code examples for every core operation, without you having to explain the ecosystem or paste in examples first.

**Prerequisites:** the [Claude Code CLI](https://claude.com/claude-code) installed (`claude --version` to check).

**Install:**

```bash
/plugin marketplace add retothuerer/LabFREED
/plugin install labfreed@labfreed-plugins
```

`retothuerer/LabFREED` (no `@ref`) resolves to this repo's default branch. If you want
the plugin content tied to a released version rather than whatever's currently in
active development, pin it explicitly instead:

```bash
/plugin marketplace add retothuerer/LabFREED@main
```

**Verify it's working:** run `/plugin` and check `labfreed` shows up under Installed —
or just ask Claude something like "what is a PAC-CAT?" or "write Python to parse this
PAC-ID" in any project; the skill should kick in on its own, without you mentioning it
by name.

**Keeping it up to date:** `/plugin marketplace update` refreshes the marketplace
listing from this repo, then `/plugin update labfreed` updates the installed plugin
itself. Plugin content is refreshed as part of every labfreed release (see
[Versioning](#versioning)).

**Uninstall:** `/plugin uninstall labfreed`.

See [plugins/labfreed/README.md](https://github.com/retothuerer/LabFREED/blob/main/plugins/labfreed/README.md) for exactly what the skill covers.

## Package Structure

The `labfreed` package is organized into three parts, reflecting how far the code strays from being a plain implementation of the building block specifications:

- **`labfreed/`** (core) — the building blocks themselves (PAC-ID, PAC-CAT, T-REX, PAC-ID Resolver, PAC-Attributes), plus the Python-specific convenience code that goes with them (e.g. converting between spec types and native Python types). Only needs the base dependencies installed by `pip install labfreed`. Units (`Quantity`, T-REX's UNECE-code mapping) are [UCUM](https://ucum.org/) throughout — the [UCUM unit validator](https://lhncbc.github.io/ucum-lhc/demo.html) is the quickest way to check whether a unit string is valid UCUM. Structural UCUM validation works with no extra dependency; automatic mapping for compound/non-SI units, full symbol-level validation, and pretty-printing additionally need the `units` extra:

  ```bash
  pip install labfreed[units]
  ```

- **`labfreed/labfreed_extended/`** — reference implementations built on top of the library that go beyond representing the specs in Python, such as a Flask-based attribute server and the PAC issuer landing page (see [Setting up a PAC-ID Landing Page](https://github.com/retothuerer/LabFREED/blob/main/examples/pac_mettorius_com/README.md)). Requires the `extended` extra:

  ```bash
  pip install labfreed[extended]
  ```

- **`labfreed/labfreed_experimental/`** — early-stage, unstable code with no compatibility guarantees (currently BLE-based PAC discovery). Requires the `experimental` extra:

  ```bash
  pip install labfreed[experimental]
  ```

## Design Philosophy

This library optimizes for ease of use over the cleanest possible architecture. Concretely:

- **Data types carry their own behavior.** Rather than keeping models as plain data holders and pushing parsing, serialization, and validation into separate classes, types like `PAC_ID`, `Quantity`, and `DataTable` expose that behavior directly as methods (`PAC_ID.from_url()`/`.to_url()`, `Quantity.from_str_value()`, `DataTable.append()`/`.get_column()`). One import, one object — no separate factory or validator to look up.
- **Few factories.** Construction from external representations (URLs, strings, payload dicts) goes through classmethods on the type itself (`from_url`, `from_str_value`, `from_payload_attributes`, ...) rather than dedicated `*Factory` classes. The handful of factories that do exist live in `labfreed_extended`, not in the core building blocks.
- **Validation lives on the model.** `LabFREED_BaseModel` gives every core type `is_valid` / `validation_messages()` / `print_validation_messages()` directly, instead of routing through an external validator.

This is a deliberate tradeoff: a stricter separation-of-concerns design would be easier to unit-test in isolation and would keep each class's responsibility narrower, but it would also mean more classes to import and more indirection to trace for what is, for most users, a small set of well-defined operations — parse an identifier, serialize it, check it's valid.

## Usage Examples
> ⚠️ **Note:** These examples are building on each other. Imports and parsing are not repeated in each example.
<!-- BEGIN EXAMPLES -->
```python
# import built ins
import os


```
### Parse a simple PAC-ID

```python
# Parse the PAC-ID
from labfreed import PAC_ID, LabFREED_ValidationError  

pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234'
try:
    pac = PAC_ID.from_url(pac_str)
except LabFREED_ValidationError:
    pass
# Check validity of this PAC-ID
is_valid = pac.is_valid
print(f'PAC-ID is valid: {is_valid}')
```
```text
>> PAC-ID is valid: True
```
### Show recommendations:
Note that the PAC-ID -- while valid -- uses characters which are not recommended (results in larger QR code).
There is a nice function to highlight problems

```python
pac.print_validation_messages()
```
```text
>> Validation Results                                                              
>> ┌──────────────────────────────────────────────────────────────────────────────┐
>> │ **RECOMMENDATION** in id segment value bal500                                │
>> │ Characters 'a','b','l' should not be used., Characters SHOULD be limited to  │
>> │ upper case letters (A-Z), numbers (0-9), '-' and '+'                         │
>> │                                                                              │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/👉bal👈500/@1234                               │
>> ├──────────────────────────────────────────────────────────────────────────────┤
>> │ **RECOMMENDATION** in id segment value @1234                                 │
>> │ Characters '@' should not be used., Characters SHOULD be limited to upper    │
>> │ case letters (A-Z), numbers (0-9), '-' and '+'                               │
>> │                                                                              │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/bal500/👉@👈1234                               │
>> ├──────────────────────────────────────────────────────────────────────────────┤
>> │ **RECOMMENDATION** in id segment value bal500                                │
>> │ Characters 'a','b','l' should not be used., Characters SHOULD be limited to  │
>> │ upper case letters (A-Z), numbers (0-9), '-' and '+'                         │
>> │                                                                              │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/👉bal👈500/@1234                               │
>> ├──────────────────────────────────────────────────────────────────────────────┤
>> │ **RECOMMENDATION** in id segment value @1234                                 │
>> │ Characters '@' should not be used., Characters SHOULD be limited to upper    │
>> │ case letters (A-Z), numbers (0-9), '-' and '+'                               │
>> │                                                                              │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/bal500/👉@👈1234                               │
>> ├──────────────────────────────────────────────────────────────────────────────┤
>> │ **RECOMMENDATION** in id segment value bal500                                │
>> │ Characters 'a','b','l' should not be used., Characters SHOULD be limited to  │
>> │ upper case letters (A-Z), numbers (0-9), '-' and '+'                         │
>> │                                                                              │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/👉bal👈500/@1234                               │
>> ├──────────────────────────────────────────────────────────────────────────────┤
>> │ **RECOMMENDATION** in id segment value @1234                                 │
>> │ Characters '@' should not be used., Characters SHOULD be limited to upper    │
>> │ case letters (A-Z), numbers (0-9), '-' and '+'                               │
>> │                                                                              │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/bal500/👉@👈1234                               │
>> └──────────────────────────────────────────────────────────────────────────────┘
```
### Save as QR Code

```python
from labfreed.qr import save_qr_with_markers  

save_qr_with_markers(pac_str, fmt='png')
```
```text
>> Large QR: Provided URL is not alphanumeric!
>> Size: 29
>> Version: 3
>> Error Level: M
```
### PAC-CAT
PAC-CAT defines a (optional) way how the identifier is structured.
PAC_ID.from_url() automatically converts to PAC-CAT if possible.

```python
from labfreed import PAC_CAT  
pac_str = 'HTTPS://PAC.METTORIUS.COM/-DR/XQ908756/-MD/bal500/@1234'
pac = PAC_ID.from_url(pac_str)
if isinstance(pac, PAC_CAT):
    categories = pac.categories 
    pac.print_categories()
```
```text
>> Categories in           
>> HTTPS://PAC.METTORIUS.COM/-DR/XQ90
>>       8756/-MD/bal500/@1234       
>> ┌────────────────────┬───────────┐
>> │ Main Category      │           │
>> │ key ()             │  -DR      │
>> │ id (21)            │  XQ908756 │
>> ├────────────────────┼───────────┤
>> │ Category           │           │
>> │ key ()             │  -MD      │
>> │ model_number (240) │  bal500   │
>> │ serial_number (21) │  @1234    │
>> └────────────────────┴───────────┘
```
### Parse a PAC-ID with extensions
PAC-ID can have extensions. Here we parse a PAC-ID with attached display names and summary.

```python
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$TEXT/WM633OV3E5DGJW2BEG0PDM1EA7*SUM$TREX/WEIGHT$GRM:67.89'
pac = PAC_ID.from_url(pac_str)
```
#### Display Name
Note that the Extension is automatically converted to a DisplayNameExtension

```python
display_name = pac.get_extension('N') # display name has name 'N'
print(display_name) 
```
```text
>> Text: My Balance ❤️
```
#### TREX

```python
trexes = pac.get_extension_of_type('TREX')
trex_extension = trexes[0] # there could be multiple trexes. In this example there is only one, though
trex = trex_extension.trex
v = trex.get_segment('WEIGHT')
print(f'WEIGHT = {v.value}')
```
```text
>> WEIGHT = 67.89
```
### Create a PAC-ID with Extensions

#### Create PAC-ID

```python
from labfreed import PAC_ID, IDSegment  
from labfreed.well_known_keys.labfreed.well_known_keys import WellKnownKeys  

pac = PAC_ID(issuer='METTORIUS.COM', identifier=[IDSegment(key=WellKnownKeys.SERIAL, value='1234')])
pac_str = pac.to_url()
print(pac_str)
```
```text
>> HTTPS://PAC.METTORIUS.COM/21:1234
```
#### Create a TREX 
TREX can conveniently be created from a python dictionary.
Note that utility types for Quantity (number with unit) and table are needed

```python
from datetime import datetime  
from labfreed.trex.facade import T_REX  
from labfreed.trex.facade import DataTable  
from labfreed.trex.facade import Quantity  
from labfreed.utilities.quantity import CommonQuantityUnit  

# Value segments of different type
# unit can be set from the CommonQuantityUnit enum (TEMP) or as a plain UCUM string (DURATION below)
segments = {
                'STOP': datetime(year=2024,month=5,day=5,hour=13,minute=6),
                'TEMP': Quantity(value=10.15, unit=CommonQuantityUnit.TEMPERATURE_KELVIN),
                'OK':False,
                'COMMENT': 'FOO',
                'COMMENT2':'£'
            }
mydata = T_REX(segments)

# Create a table
table = DataTable(col_names=['DURATION', 'Date', 'OK', 'COMMENT'])
table.append([Quantity(value=1, unit='h'), datetime.now(), True, 'FOO'])
table.append([                                                 1.1,  datetime.now(), True, 'BAR'])
table.append([                                                 1.3,  datetime.now(), False, 'BLUBB'])
#add the table to the pytrex
mydata.update({'TABLE': table})

# Create TREX
trex = mydata.to_trex()


# Validation also works the same way for TREX
trex.print_validation_messages()
```
```text
>> Validation Results                                            
>> ┌────────────────────────────────────────────────────────────┐
>> │ **ERROR** in TREX table column Date                        │
>> │ Column header key contains invalid characters: 'a','t','e' │
>> │                                                            │
>> │ STOP$T.D:20240505T1306                                     │
>> │ +TEMP$KEL:10.15                                            │
>> │ +OK$T.B:F                                                  │
>> │ +COMMENT$T.A:FOO                                           │
>> │ +COMMENT2$T.T:12G3                                         │
>> │ +TABLE$$DURATION$HUR:D👉ate👈$T.D:OK$T.B:COMMENT$T.A::     │
>> │  1:20260803T073633.966:T:FOO::                             │
>> │  1.1:20260803T073633.966:T:BAR::                           │
>> │  1.3:20260803T073633.968:F:BLUBB                           │
>> └────────────────────────────────────────────────────────────┘
```
#### Combine PAC-ID and TREX and serialize

```python
from labfreed.well_known_extensions import TREX_Extension  
pac.extensions = [TREX_Extension(name='MYTREX', trex=trex)]
pac_str = pac.to_url()
print(pac_str)
```
```text
>> HTTPS://PAC.METTORIUS.COM/21:1234*MYTREX$TREX/STOP$T.D:20240505T1306+TEMP$KEL:10.15+OK$T.B:F+COMMENT$T.A:FOO+COMMENT2$T.T:12G3+TABLE$$DURATION$HUR:Date$T.D:OK$T.B:COMMENT$T.A::1:20260803T073633.966:T:FOO::1.1:20260803T073633.966:T:BAR::1.3:20260803T073633.968:F:BLUBB
```
## PAC-ID Resolver

```python
from labfreed import PAC_ID_Resolver, load_cit  
from labfreed.pac_id_resolver.service_availability import check_service_group  
import requests_cache

# Get a CIT
dir = os.path.join(os.getcwd(), 'examples')
p = os.path.join(dir, 'cit_mine.yaml')       
cit = load_cit(p)

# validate the CIT
cit.is_valid
cit.print_validation_messages()
```
```python
# get a second cit
p = os.path.join(dir, 'coupling-information-table')
cit2 = load_cit(p)
cit2.origin = 'MY_COMPANY'
```
```python
# resolve a pac id
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MS/X3511/CAS:7732-18-5'
service_groups = PAC_ID_Resolver(resolver_configs=[cit, cit2]).resolve(pac_str, check_service_status=False)
cached_session = requests_cache.CachedSession(backend='memory', expire_after=60)
for sg in service_groups:
    check_service_group(sg, cached_session)
    sg.print()
```
```text
>> Services from origin 'MY_COMPANY                        
>> ┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
>> ┃ Service Name        ┃ URL                  ┃ Service Type        ┃ Reachable ┃
>> ┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
>> │ Chemical Management │ https://chem-manage… │ userhandover-gener… │ UNKNOWN   │
>> └─────────────────────┴──────────────────────┴─────────────────────┴───────────┘
>>                          Services from origin 'PERSONAL                         
>> ┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
>> ┃ Service Name ┃ URL                        ┃ Service Type         ┃ Reachable ┃
>> ┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
>> │ CAS Search   │ https://pubchem.ncbi.nlm.… │ userhandover-generic │ UNKNOWN   │
>> └──────────────┴────────────────────────────┴──────────────────────┴───────────┘
```
## PAC-ID Attributes
Attributes attach lightweight metadata -- e.g. a display name, an image, a calibration due date -- to a PAC-ID,
without baking it into the identifier itself.

This shows the core data model only: an in-memory data source, served in-process with no Flask/network involved.
For an actual deployable server and a PAC-ID landing page built on the same classes, see
[Setting up a PAC-ID Landing Page](https://github.com/retothuerer/LabFREED/blob/main/examples/pac_mettorius_com/README.md).

```python
from labfreed.pac_attributes.facade.attributes import Attribute, Attributes, Resource  
from labfreed.pac_attributes.facade.dict_data_source import Dict_DataSource  
from labfreed.pac_attributes.well_known_attribute_keys import MetaAttributeKeys  
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource  
from labfreed.pac_attributes.server.server import AttributeServerRequestHandler  
from labfreed.pac_attributes.client.client import AttributeClient, local_attribute_request_callback_factory  
from labfreed.utilities.translations import Terms, Term  

# Attributes for one PAC-ID. A data source could just as well read this from a database, an Excel sheet, or anywhere else.
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001'
data_source = Dict_DataSource(
    attribute_group_key=MetaAttributeKeys.GROUPKEY,
    data={
        pac_str: Attributes([
            Attribute(key=MetaAttributeKeys.DISPLAYNAME, value="My Balance"),
            Attribute(key=MetaAttributeKeys.IMAGE, value=Resource("https://picsum.photos/id/82/200")),
        ])
    }
)

# Attribute keys need a translation, so the server can label them for a UI
translations = DictTranslationDataSource(
    supported_languages={'en'},
    data=Terms(terms=[
        Term.create(MetaAttributeKeys.GROUPKEY, [('en', 'Meta Data')]),
        Term.create(MetaAttributeKeys.DISPLAYNAME, [('en', 'Display Name')]),
        Term.create(MetaAttributeKeys.IMAGE, [('en', 'Image')]),
    ])
)

# The request handler is the framework-agnostic core of an attribute server
handler = AttributeServerRequestHandler(data_sources=[data_source], translation_data_sources=[translations], default_language='en')
```
Querying works the same whether the handler above is embedded in a Flask app or, as here, called in-process.

```python
client = AttributeClient(http_post_callback=local_attribute_request_callback_factory(handler))
attribute_groups = client.get_attributes(server_url='', subject_id=pac_str)
for group in attribute_groups:
    for attr in Attributes.from_payload_attributes(group.attributes):
        values = ', '.join(str(v) for v in attr.value_list)
        print(f'{attr.label}: {values}')
```
```text
>> Display Name: My Balance
>> Image: https://picsum.photos/id/82/200
```
<!-- END EXAMPLES -->

## Versioning

This package follows [Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`.

- **MAJOR** -- may introduce breaking changes. A major bump doesn't have to break
  anything, but it's where we reserve the right to.
- **MINOR** -- adds functionality. We aim for backward compatibility here too, but
  reserve the right to break edge cases where keeping compatibility isn't practical
  (e.g. tightening validation on input that was already spec-invalid). Any such case is
  called out explicitly in the changelog as `BREAKING`.
- **PATCH** -- bugfixes only, no intentional API changes.

**Deprecation policy:** when a public API needs to change or go away, we deprecate it
first -- it keeps working, but raises a `DeprecationWarning` pointing at its
replacement -- and keep that deprecated path working for at least one more major
version before actually removing it.

**Pre-releases:** in-progress work toward the next version is published straight to
[PyPI](https://pypi.org/project/labfreed/) as an alpha/beta pre-release (e.g.
`1.0.0b44`). A plain `pip install labfreed` always resolves to the latest stable release
and skips these automatically -- opt in explicitly with `pip install --pre labfreed`, or
pin an exact pre-release (`pip install labfreed==1.0.0b44`). Since the LabFREED
building-block specs and this implementation are co-developed, a pre-release can be
ahead of the currently *published* spec -- it may reflect a spec that's still being
drafted. Treat pre-release behavior as experimental and subject to change before the
real release ships.

<!-- BEGIN CHANGELOG -->
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
- BREAKING: `labfreed.trex.pythonic` and `labfreed.pac_attributes.pythonic` renamed to `labfreed.trex.facade` and `labfreed.pac_attributes.facade`; every `py`-prefixed convenience class (`pyTREX`, `pyAttribute`, `pyAttributes`, `pyResource`, `pyReference`, `pyDict_DataSource`) renamed to drop the `py` prefix (`T_REX`, `Attribute`, `Attributes`, `Resource`, `Reference`, `Dict_DataSource`) - old names kept as deprecated aliases for one more major version, but the old `labfreed.*.pythonic` submodule path itself is gone entirely, not just the symbol names
- BREAKING: renamed Quantity.float property to Quantity.as_float (the name collided with the float type used in Quantity's own annotations, breaking model construction on Python 3.14)
- moved `Quantity` from `labfreed.trex.pythonic.quantity` to `labfreed.utilities.quantity` (it's used by PAC-ID Attributes too, not only T-REX); also reachable via `labfreed.trex.facade` alongside `T_REX`/`DataTable` - `unece_unit_code_from_quantity` (T-REX-specific) moved into `pyTREX.py`
- `AttributeClient.get_attributes()`'s `pac_id` parameter renamed to `subject_id`, matching the rest of the IRI migration - old `pac_id=` keyword still works via a deprecated shim
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
<!-- END CHANGELOG -->

## Getting Help / FAQ

- **Questions about the LabFREED building blocks themselves** (PAC-ID, PAC-CAT, T-REX,
  PAC-ID Resolver, PAC-ID Attributes) — join the community
  [Discord](https://discord.com/invite/bxAghUAHFE) or see [labfreed.org](https://labfreed.org/).
- **Bugs or feature requests for this Python package** — open a
  [GitHub issue](https://github.com/retothuerer/LabFREED/issues).
- **Found a security issue?** See [SECURITY.md](https://github.com/retothuerer/LabFREED/blob/main/SECURITY.md) instead of opening a public issue.
- **Looking for the full API reference** (all classes/functions, generated from docstrings via
  [pdoc](https://pdoc.dev/))? It's published at
  [retothuerer.github.io/LabFREED](https://retothuerer.github.io/LabFREED/).

## Contributing

See [CONTRIBUTING.md](https://github.com/retothuerer/LabFREED/blob/main/CONTRIBUTING.md) for setting up a dev environment, running the test
suite, and what's expected of a pull request.

# Attributions
The following tools were used:
- [pdoc](https://pdoc.dev/) was a great help with generating documentation
- [Pydantic](https://docs.pydantic.dev/latest/)
- json with UNECE units from (https://github.com/quadient/unece-units/blob/main/python/src/unece_excel_parser/parsedUneceUnits.json)
- json with GS1 codes from (https://ref.gs1.org/ai/GS1_Application_Identifiers.jsonld)

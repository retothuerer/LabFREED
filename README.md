# LabFREED for Python

[![PyPI](https://img.shields.io/pypi/v/labfreed.svg)](https://pypi.org/project/labfreed/) ![Python Version](https://img.shields.io/pypi/pyversions/labfreed) [![Test Labfreed](https://github.com/retothuerer/LabFREED/actions/workflows/run-tests.yml/badge.svg)](https://github.com/retothuerer/LabFREED/actions/workflows/run-tests.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) 


This is a Python implementation of [LabFREED](https://labfreed.org/) building blocks.

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
  - support for CIT v1
  - draft support for CIT v2 (improved version)
  - combined use of multiple cit in any combination of version
- Generation of QR codes (PAC-ID with extensions)
  
- Validation (with Errors Recommendations)

## Installation
You can install LabFREED from [PyPI](https://pypi.org/project/labfreed/) using pip:

```bash
pip install labfreed
```


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
>> ┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
>> │ **RECOMMENDATION** in id segment value bal500                                                                                     │
>> │ Characters 'b','l','a' should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+'  │
>> │                                                                                                                                   │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/👉bal👈500/@1234                                                                                    │
>> ├───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
>> │ **RECOMMENDATION** in id segment value @1234                                                                                      │
>> │ Characters '@' should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+'          │
>> │                                                                                                                                   │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/bal500/👉@👈1234                                                                                    │
>> ├───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
>> │ **RECOMMENDATION** in id segment value bal500                                                                                     │
>> │ Characters 'b','l','a' should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+'  │
>> │                                                                                                                                   │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/👉bal👈500/@1234                                                                                    │
>> ├───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
>> │ **RECOMMENDATION** in id segment value @1234                                                                                      │
>> │ Characters '@' should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+'          │
>> │                                                                                                                                   │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/bal500/👉@👈1234                                                                                    │
>> └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
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
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/WM633OV3E5DGJW2BEG0PDM1EA7*SUM$TREX/WEIGHT$GRM:67.89'
pac = PAC_ID.from_url(pac_str)
```
#### Display Name
Note that the Extension is automatically converted to a DisplayNameExtension

```python
display_name = pac.get_extension('N') # display name has name 'N'
print(display_name) 
```
```text
>> Display name: My Balance ❤️
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
from labfreed.trex.python_convenience import pyTREX  
from labfreed.trex.python_convenience import DataTable  
from labfreed.trex.python_convenience import Quantity  

# Value segments of different type
segments = {
                'STOP': datetime(year=2024,month=5,day=5,hour=13,minute=6),
                'TEMP': Quantity(value=10.15, unit= 'K'),
                'OK':False,
                'COMMENT': 'FOO',
                'COMMENT2':'£'
            }
mydata = pyTREX(segments) 

# Create a table
table = DataTable(col_names=['DURATION', 'Date', 'OK', 'COMMENT'])
table.append([Quantity(value=1, unit= 'hour'), datetime.now(), True, 'FOO'])
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
>> │ Column header key contains invalid characters: 't','e','a' │
>> │                                                            │
>> │ STOP$T.D:20240505T1306                                     │
>> │ +TEMP$KEL:10.15                                            │
>> │ +OK$T.B:F                                                  │
>> │ +COMMENT$T.A:FOO                                           │
>> │ +COMMENT2$T.T:12G3                                         │
>> │ +TABLE$$DURATION$HUR:D👉ate👈$T.D:OK$T.B:COMMENT$T.A::     │
>> │  1:20250514T102232.171:T:FOO::                             │
>> │  1.1:20250514T102232.171:T:BAR::                           │
>> │  1.3:20250514T102232.171:F:BLUBB                           │
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
>> HTTPS://PAC.METTORIUS.COM/21:1234*MYTREX$TREX/STOP$T.D:20240505T1306+TEMP$KEL:10.15+OK$T.B:F+COMMENT$T.A:FOO+COMMENT2$T.T:12G3+TABLE$$DURATION$HUR:Date$T.D:OK$T.B:COMMENT$T.A::1:20250514T102232.171:T:FOO::1.1:20250514T102232.171:T:BAR::1.3:20250514T102232.171:F:BLUBB
```
## PAC-ID Resolver

```python
from labfreed import PAC_ID_Resolver, load_cit  
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
service_groups = PAC_ID_Resolver(cits=[cit, cit2]).resolve(pac_str, check_service_status=False)
cached_session = requests_cache.CachedSession(backend='memory', expire_after=60)
for sg in service_groups:
    sg.update_states(cached_session)
    sg.print()
    
```
```text
>> Services from origin 'PERSONAL                         
>> ┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
>> ┃ Service Name ┃ URL                                               ┃ Reachable ┃
>> ┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
>> │ CAS Search   │ https://pubchem.ncbi.nlm.nih.gov/#query=7732-18-5 │ ACTIVE    │
>> └──────────────┴───────────────────────────────────────────────────┴───────────┘
>>                                   Services from origin 'MY_COMPANY                                  
>> ┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
>> ┃ Service Name        ┃ URL                                                            ┃ Reachable ┃
>> ┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
>> │ Chemical Management │ https://chem-manager.com/METTORIUS.COM/-MS/X3511/CAS:7732-18-5 │ INACTIVE  │
>> └─────────────────────┴────────────────────────────────────────────────────────────────┴───────────┘
>>              Services from origin 'METTORIUS.COM              
>> ┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
>> ┃ Service Name ┃ URL                             ┃ Reachable ┃
>> ┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
>> │ CoA          │ https://mettorius.com/CoA.pdf   │ ACTIVE    │
>> │ MSDS         │ https://mettorius.com/MSDS.pdf  │ ACTIVE    │
>> │ Shop         │ https://mettorius.com/shop.html │ ACTIVE    │
>> └──────────────┴─────────────────────────────────┴───────────┘
```
<!-- END EXAMPLES -->



<!-- BEGIN CHANGELOG -->
## Change Log
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

# Attributions
The following tools were used:
- [pdoc](https://pdoc.dev/) was a great help with generating documentation
- [Pydantic](https://docs.pydantic.dev/latest/)
- json with UNECE units from (https://github.com/quadient/unece-units/blob/main/python/src/unece_excel_parser/parsedUneceUnits.json)
- json with GS1 codes from (https://ref.gs1.org/ai/GS1_Application_Identifiers.jsonld)

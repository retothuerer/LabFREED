# LabFREED for Python

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![PyPI](https://img.shields.io/pypi/v/labfreed.svg)](https://pypi.org/project/labfreed/) ![Python Version](https://img.shields.io/pypi/pyversions/labfreed)

<!--
[![Tests](https://github.com/retothuerer/LabFREED/actions/workflows/ci.yml/badge.svg)](https://github.com/retothuerer/LabFREED/actions/workflows/ci.yml)
-->

This is a Python implementation of [LabFREED](https://labfreed.wega-it.com) building blocks.

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
  - draft support for CIT v1 (improved version)
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

target = 'console'
```
### Parse a simple PAC-ID

```python
# Parse the PAC-ID
from labfreed.labfreed_infrastructure import LabFREED_ValidationError  # noqa: E402
from labfreed import PAC_ID, LabFREED_ValidationError  # noqa: E402, F811

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
pac.print_validation_messages(target=target)
```
```text
>> Validation Results                                                                                                                   
>> ┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
>> │ RECOMMENDATION  in id segment value bal500                                                                                        │
>> │ Characters 'b','a','l' should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+'  │
>> │                                                                                                                                   │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/240:bal500/21:@1234                                                                                 │
>> ├───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
>> │ RECOMMENDATION  in id segment value @1234                                                                                         │
>> │ Characters '@' should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+'          │
>> │                                                                                                                                   │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/240:bal500/21:@1234                                                                                 │
>> ├───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
>> │ RECOMMENDATION  in id segment value bal500                                                                                        │
>> │ Characters 'b','a','l' should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+'  │
>> │                                                                                                                                   │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/240:bal500/21:@1234                                                                                 │
>> ├───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
>> │ RECOMMENDATION  in id segment value @1234                                                                                         │
>> │ Characters '@' should not be used., Characters SHOULD be limited to upper case letters (A-Z), numbers (0-9), '-' and '+'          │
>> │                                                                                                                                   │
>> │ HTTPS://PAC.METTORIUS.COM/-MD/240:bal500/21:@1234                                                                                 │
>> └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```
### Save as QR Code

```python
from labfreed.qr import save_qr_with_markers  # noqa: E402

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
from labfreed.pac_cat import PAC_CAT  # noqa: E402
pac_str = 'HTTPS://PAC.METTORIUS.COM/-DR/XQ908756/-MD/bal500/@1234'
pac = PAC_ID.from_url(pac_str)
if isinstance(pac, PAC_CAT):
    categories = pac.categories 
    pac.print_categories()
```
```text
>> Categories in           
>> HTTPS://PAC.METTORIUS.COM/-MD/240:
>>          bal500/21:@1234          
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
from labfreed.pac_id import PAC_ID, IDSegment  # noqa: E402
from labfreed.well_known_keys.labfreed.well_known_keys import WellKnownKeys  # noqa: E402

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
from datetime import datetime  # noqa: E402
from labfreed.trex.python_convenience.pyTREX import pyTREX  # noqa: E402
from labfreed.trex.python_convenience.data_table import DataTable  # noqa: E402
from labfreed.trex.python_convenience.quantity import Quantity  # noqa: E402

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
trex.print_validation_messages(target=target)
```
```text
>> Validation Results                                            
>> ┌────────────────────────────────────────────────────────────┐
>> │ ERROR  in TREX table column Date                           │
>> │ Column header key contains invalid characters: 'a','t','e' │
>> │                                                            │
>> │ STOP$T.D:20240505T1306                                     │
>> │ +TEMP$KEL:10.15                                            │
>> │ +OK$T.B:F                                                  │
>> │ +COMMENT$T.A:FOO                                           │
>> │ +COMMENT2$T.T:QMDTNXIKU                                    │
>> │ +TABLE$$DURATION$HUR:Date$T.D:OK$T.B:COMMENT$T.A::         │
>> │  1:20250423T142912.783:T:FOO::                             │
>> │  1.1:20250423T142912.783:T:BAR::                           │
>> │  1.3:20250423T142912.783:F:BLUBB                           │
>> └────────────────────────────────────────────────────────────┘
```
#### Combine PAC-ID and TREX and serialize

```python
from labfreed.well_known_extensions import TREX_Extension  # noqa: E402
pac.extensions = [TREX_Extension(name='MYTREX', trex=trex)]
pac_str = pac.to_url()
print(pac_str)
```
```text
>> HTTPS://PAC.METTORIUS.COM/21:1234*MYTREX$TREX/STOP$T.D:20240505T1306+TEMP$KEL:10.15+OK$T.B:F+COMMENT$T.A:FOO+COMMENT2$T.T:QMDTNXIKU+TABLE$$DURATION$HUR:Date$T.D:OK$T.B:COMMENT$T.A::1:20250423T142912.783:T:FOO::1.1:20250423T142912.783:T:BAR::1.3:20250423T142912.783:F:BLUBB
```
## PAC-ID Resolver

```python
from labfreed.pac_id_resolver import PAC_ID_Resolver, load_cit  # noqa: E402
# Get a CIT
dir = os.path.join(os.getcwd(), 'examples')
p = os.path.join(dir, 'cit_mine.yaml')       
cit = load_cit(p)

# validate the CIT
cit.is_valid
cit.print_validation_messages(target=target)
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
service_groups = PAC_ID_Resolver(cits=[cit, cit2]).resolve(pac_str)
for sg in service_groups:
    sg.update_states()
    sg.print()
    
```
```text
>> Services from origin 'PERSONAL                         
>> ┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
>> ┃ Service Name ┃ URL                                               ┃ Reachable ┃
>> ┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
>> │ CAS Search   │ https://pubchem.ncbi.nlm.nih.gov/#query=7732-18-5 │ ACTIVE    │
>> └──────────────┴───────────────────────────────────────────────────┴───────────┘
>>                                     Services from origin 'MY_COMPANY                                    
>> ┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
>> ┃ Service Name        ┃ URL                                                                ┃ Reachable ┃
>> ┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
>> │ Chemical Management │ https://chem-manager.com/METTORIUS.COM/-MS/240:X3511/CAS:7732-18-5 │ INACTIVE  │
>> └─────────────────────┴────────────────────────────────────────────────────────────────────┴───────────┘
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



## Change Log
[> Change Log](/CHANGELOG.md)

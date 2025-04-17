# LabFREED for Python

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![PyPI](https://img.shields.io/pypi/v/labfreed.svg)](https://pypi.org/project/labfreed/) ![Python Version](https://img.shields.io/pypi/pyversions/labfreed)

<!--
[![Tests](https://github.com/retothuerer/LabFREED/actions/workflows/ci.yml/badge.svg)](https://github.com/retothuerer/LabFREED/actions/workflows/ci.yml)
-->

This is a Python implementation of [LabFREED](https://labfreed.wega-it.com) building blocks.

## Supported Building Blocks
- PAC-ID
  - Parsing
  - Validation (with Errors Recommendations)
  - Serialization
- PAC-CAT
  - Interpretation of PAC-ID as categories
  - Validation (with Errors Recommendations)
- T-REX
  - Parsing 
  - Validation (with Errors Recommendations)
  - Serialization
- Display Extension
  - base36 <> str conversions
- PAC-ID Resolver
- Generation of QR codes (PAC-ID with extensions)

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
from labfreed.IO.parse_pac import PAC_Parser


# Parse the PAC-ID
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234'
pac_id = PAC_Parser().parse(pac_str).pac_id

# Check validity of this PAC-ID
is_valid = pac_id.is_valid
print(f'PAC-ID is valid: {is_valid}')
```
```text
>> [Error during execution: No module named 'labfreed']
```
### Show recommendations:
Note that the PAC-ID -- while valid -- uses characters which are not recommended (results in larger QR code).
There is a nice function to highlight problems

```python
pac_id.print_validation_messages(target=target)
```
```text
>> [Error during execution: name 'pac_id' is not defined]
```
### Save as QR Code

```python
from labfreed.IO.generate_qr import save_qr_with_markers

save_qr_with_markers(pac_str, fmt='png')
```
```text
>> [Error during execution: No module named 'labfreed']
```
### PAC-CAT

```python
from labfreed.pac_cat import PAC_CAT
pac_str = 'HTTPS://PAC.METTORIUS.COM/-DR/XQ908756/-MD/bal500/@1234'
pac_id = PAC_Parser().parse(pac_str).pac_id
if isinstance(pac_id, PAC_CAT):
    pac_id.print_categories()
```
```text
>> [Error during execution: No module named 'labfreed']
```
### Parse a PAC-ID with extensions
PAC-ID can have extensions. Here we parse a PAC-ID with attached display names and summary.

```python
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/WM633OV3E5DGJW2BEG0PDM1EA7*SUM$TREX/WEIGHT$GRM:67.89'
pac_id = PAC_Parser().parse(pac_str)

# Display Name
display_names = pac_id.get_extension('N') # display name has name 'N'
print(display_names)
```
```text
>> [Error during execution: name 'PAC_Parser' is not defined]
```
```python
# TREX
trexes = pac_id.get_extension_of_type('TREX')
trex = trexes[0] # there could be multiple trexes. In this example there is only one, though
v = trex.get_segment('WEIGHT').to_python_type() 
print(f'WEIGHT = {v}')
```
```text
>> [Error during execution: name 'pac_id' is not defined]
```
### Create a PAC-ID with Extensions

#### Create PAC-ID

```python
from labfreed.pac_id import PACID, IDSegment
from labfreed.utilities.well_known_keys import WellKnownKeys

pac_id = PACID(issuer='METTORIUS.COM', identifier=[IDSegment(key=WellKnownKeys.SERIAL, value='1234')])
pac_str = pac_id.serialize()
print(pac_str)
```
```text
>> [Error during execution: No module named 'labfreed']
```
#### Create a TREX 
TREX can conveniently be created from a python dictionary.
Note that utility types for Quantity (number with unit) and table are needed

```python
from datetime import datetime
from labfreed.trex.trex_base_models import TREX
from labfreed.utilities.utility_types import Quantity, DataTable, Unit

# Create TREX
trex = TREX(name_='DEMO') 
# Add value segments of different type
trex.update(   
                    {
                        'STOP': datetime(year=2024,month=5,day=5,hour=13,minute=6),
                        'TEMP': Quantity(value=10.15, unit=Unit(name='kelvin', symbol='K')),
                        'OK':False,
                        'COMMENT': 'FOO',
                        'COMMENT2':'£'
                    }
)

# Create a table
table = DataTable(['DURATION', 'Date', 'OK', 'COMMENT'])
table.append([Quantity(value=1, unit=Unit(symbol='h', name='hour')), datetime.now(), True, 'FOO'])
table.append([                                                 1.1,  datetime.now(), True, 'BAR'])
table.append([                                                 1.3,  datetime.now(), False, 'BLUBB'])
#add the table to the trex
trex.update({'TABLE': table})

# Validation also works the same way for TREX
trex.print_validation_messages(target=target)
```
```text
>> [Error during execution: No module named 'labfreed']
```
```python
# there is an error. 'Date' uses lower case. Lets fix it
d = trex.to_dict()
d['TABLE'].col_names[1] = 'DATE'
trex = TREX(name_='DEMO') 
trex.update(d)
```
```text
>> [Error during execution: name 'trex' is not defined]
```
#### Combine PAC-ID and TREX and serialize

```python
from labfreed.IO.parse_pac import PACID_With_Extensions

pac_with_trex = PACID_With_Extensions(pac_id=pac_id, extensions=[trex])
pac_str = pac_with_trex.serialize()
print(pac_str)
```
```text
>> [Error during execution: No module named 'labfreed']
```
## PAC-ID Resolver

```python
from labfreed.PAC_ID_Resolver.resolver import PAC_ID_Resolver, load_cit
# Get a CIT
dir = os.path.dirname(__file__)
p = os.path.join(dir, 'cit_mine.yaml')       
cit = load_cit(p)

# validate the CIT
cit.is_valid
cit.print_validation_messages(target=target)
```
```text
>> [Error during execution: No module named 'labfreed']
```
```python
# resolve a pac id
service_groups = PAC_ID_Resolver(cits=[cit]).resolve(pac_with_trex)
for sg in service_groups:
    sg.update_states()
    sg.print()
    
```
```text
>> [Error during execution: name 'PAC_ID_Resolver' is not defined]
```
<!-- END EXAMPLES -->



## Change Log

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

# Attributions
The following tools were used:
- Json with UNECE units from (https://github.com/quadient/unece-units/blob/main/python/src/unece_excel_parser/parsedUneceUnits.json)
- Json with GS1 codes from (https://ref.gs1.org/ai/GS1_Application_Identifiers.jsonld)
- [pdoc](https://pdoc.dev/) was a great help with generating documentation
- [Pydantic](https://docs.pydantic.dev/latest/)


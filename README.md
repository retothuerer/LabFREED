# LabFREED for Python

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![PyPI](https://img.shields.io/pypi/v/labfreed.svg)](https://pypi.org/project/labfreed/) ![Python Version](https://img.shields.io/pypi/pyversions/labfreed)

<!--
[![Tests](https://github.com/retothuerer/LabFREED/actions/workflows/ci.yml/badge.svg)](https://github.com/retothuerer/LabFREED/actions/workflows/ci.yml)
-->

This is a Python implementation of [LabFREED](www.labfreed.wega-it.com) building blocks.

## Supported Building Blocks
- PAC-ID
- PAC-CAT
- TREX
- Display Extension

## Installation
You can install LabFREED from [PyPI](https://pypi.org/project/labfreed/) using pip:

```bash
pip install labfreed
```


## Usage Examples
<!-- BEGIN EXAMPLES -->
```python

```

### Parse a simple PAC-ID 
The

```python
from labfreed.parse_pac import PAC_Parser

# Parse the PAC-ID
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234'
pac_id = PAC_Parser().parse(pac_str).pac_id

# Check validity of this PAC-ID
pac_id = PAC_Parser().parse(pac_str).pac_id
is_valid = pac_id.is_valid()
print('PAC-ID is valid: {is_valid}')
# >> PAC-ID is valid: {is_valid}
```

Show recommendations:
Note that the PAC-ID, while valid uses characters, which are not recommended (results in larger QR code).
There is a nice function to highlight problems

```python
pac_id.print_validation_messages()
# >>
#   =======================================
#   Validation Results
#   ---------------------------------------

#   Recommendation  in      id segment value bal500
#   HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234
#   Characters a b l should not be used.

#   Recommendation  in      id segment value @1234
#   HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234
#   Characters @ should not be used.

#   Warning  in     Category -MD
#   HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234
#   Category key -MD is not a well known key. It is recommended to use well known keys only
```

### Parse a PAC-ID with extensions
PAC-ID can have extensions. Here we parse a PAC-ID with attached display names and summary.

```python
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/WM633OV3E5DGJW2BEG0PDM1EA7*SUM$TREX/WEIGHT$GRM:67.89'
pac_id = PAC_Parser().parse(pac_str)

# Display Name
display_names = pac_id.get_extension('N') # display name has name 'N'
print(f'\n {display_names}')
# >> Display names: My Balance ❤️

# TREX
trexes = pac_id.get_extension_of_type('TREX')
trex = trexes[0] # there could be multiple trexes. In this example there is only one, though
v = trex.get_segment('WEIGHT').to_python_type() 
print(f'WEIGHT = {v}')
# >> WEIGHT = 67.89 g
```

### Create a PAC-ID with Extensions

#### Create PAC-ID

```python
from labfreed.PAC_ID.data_model import PACID, IDSegment
from labfreed.utilities.well_known_keys import WellKnownKeys

pac_id = PACID(issuer='METTORIUS:COM', identifier=[IDSegment(key=WellKnownKeys.SERIAL, value='1234')])
pac_str = pac_id.serialize()
pac_str = pac_id.serialize()
print(pac_str)
```

#### Create a TREX 
TREX can conveniently be created from a python dictionary.
Note that utility types for Quantity (number with unit) and table are needed

```python
from datetime import datetime
from labfreed.TREX.data_model import TREX
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
table = DataTable(['DURATION', 'DATE', 'OK', 'COMMENT'])
table.append([Quantity(value=1, unit=Unit(symbol='h', name='hour')), datetime.now(), True, 'FOO'])
table.append([                                                 1.1,  datetime.now(), True, 'BAR'])
table.append([                                                 1.3,  datetime.now(), False, 'BLUBB'])
#add the table to the trex
trex.update({'TABLE': table})

# Validation also works the same way for TREX
if trex.get_nested_validation_messages():
    trex.print_validation_messages()

# Side Note: The TREX can be turned back into a dict
d = trex.dict()
```

#### Combine PAC-ID and TREX and serialize

```python
from labfreed.parse_pac import PACID_With_Extensions

pac_with_trex = PACID_With_Extensions(pac_id=pac_id, extensions=[trex])
pac_str = pac_with_trex.serialize()
print(pac_str)
```

<!-- END EXAMPLES -->



## Change Log

### v0.0.9
- supports PAC-ID, PAC-CAT, TREX and DisplayName
- ok-ish test coverage
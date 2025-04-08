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

# Parse a PAC ID
from labfreed.PAC_ID.parse import PAC_Parser
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234'
pac = PAC_Parser().parse_pac_id(pac_str)

## Check validity
pac.is_valid()
pac.print_validation_messages()


## Parse a PAC-ID with extensions
from labfreed.utilities.extension_intertpreters import well_known_interpreters as extension_interpreters
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*NAME$N/WM633OV3E5DGJW2BEG0PDM1EA7*SUM$TREX/WEIGHT$GRM:67.89'
pac = PAC_Parser(extension_interpreters).parse_pac_id(pac_str)

## Create a PAC-ID

## Create a PAC-ID and T-REX for a titration curve



```

<!-- END EXAMPLES -->



## Change Log

### v0.0.9
- supports PAC-ID, PAC-CAT, TREX and DisplayName
- ok-ish test coverage
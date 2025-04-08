''' 
### Parse a simple PAC-ID 
'''
from labfreed.parse_pac import PAC_Parser

# Parse the PAC-ID
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234'
pac_id = PAC_Parser().parse(pac_str).pac_id

# Check validity of this PAC-ID
pac_id = PAC_Parser().parse(pac_str).pac_id
is_valid = pac_id.is_valid()
print('PAC-ID is valid: {is_valid}')

''' 
### Show recommendations:
Note that the PAC-ID -- while valid -- uses characters which are not recommended (results in larger QR code).
There is a nice function to highlight problems
'''
pac_id.print_validation_messages()


'''
### PAC-CAT
'''
from labfreed.PAC_CAT.data_model import PAC_CAT
pac_str = 'HTTPS://PAC.METTORIUS.COM/-DR/XQ908756/-MD/bal500/@1234'
pac_id = PAC_Parser().parse(pac_str).pac_id
if isinstance(pac_id, PAC_CAT):
    pac_id.print_categories()





''' 
### Parse a PAC-ID with extensions
PAC-ID can have extensions. Here we parse a PAC-ID with attached display names and summary.
'''
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/WM633OV3E5DGJW2BEG0PDM1EA7*SUM$TREX/WEIGHT$GRM:67.89'
pac_id = PAC_Parser().parse(pac_str)

# Display Name
display_names = pac_id.get_extension('N') # display name has name 'N'
print(display_names)

''''''
# TREX
trexes = pac_id.get_extension_of_type('TREX')
trex = trexes[0] # there could be multiple trexes. In this example there is only one, though
v = trex.get_segment('WEIGHT').to_python_type() 
print(f'WEIGHT = {v}')



''' 
### Create a PAC-ID with Extensions

#### Create PAC-ID
'''
from labfreed.PAC_ID.data_model import PACID, IDSegment
from labfreed.utilities.well_known_keys import WellKnownKeys

pac_id = PACID(issuer='METTORIUS:COM', identifier=[IDSegment(key=WellKnownKeys.SERIAL, value='1234')])
pac_str = pac_id.serialize()
print(pac_str)


''' 
#### Create a TREX 
TREX can conveniently be created from a python dictionary.
Note that utility types for Quantity (number with unit) and table are needed
'''
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

''' 
#### Combine PAC-ID and TREX and serialize
'''
from labfreed.parse_pac import PACID_With_Extensions

pac_with_trex = PACID_With_Extensions(pac_id=pac_id, extensions=[trex])
pac_str = pac_with_trex.serialize()
print(pac_str)






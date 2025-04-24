# import built ins
import os

target = 'markdown'
''' 
### Parse a simple PAC-ID 
'''
# Parse the PAC-ID
from labfreed import PAC_ID, LabFREED_ValidationError  # noqa: E402

pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234'
try:
    pac = PAC_ID.from_url(pac_str)
except LabFREED_ValidationError:
    pass
# Check validity of this PAC-ID
is_valid = pac.is_valid
print(f'PAC-ID is valid: {is_valid}')


''' 
### Show recommendations:
Note that the PAC-ID -- while valid -- uses characters which are not recommended (results in larger QR code).
There is a nice function to highlight problems
'''
pac.print_validation_messages(target=target)

'''
### Save as QR Code
'''
from labfreed.qr import save_qr_with_markers  # noqa: E402

save_qr_with_markers(pac_str, fmt='png')

'''
### PAC-CAT
PAC-CAT defines a (optional) way how the identifier is structured.
PAC_ID.from_url() automatically converts to PAC-CAT if possible.
'''
from labfreed import PAC_CAT  # noqa: E402
pac_str = 'HTTPS://PAC.METTORIUS.COM/-DR/XQ908756/-MD/bal500/@1234'
pac = PAC_ID.from_url(pac_str)
if isinstance(pac, PAC_CAT):
    categories = pac.categories 
    pac.print_categories()




''' 
### Parse a PAC-ID with extensions
PAC-ID can have extensions. Here we parse a PAC-ID with attached display names and summary.
'''
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/WM633OV3E5DGJW2BEG0PDM1EA7*SUM$TREX/WEIGHT$GRM:67.89'
pac = PAC_ID.from_url(pac_str)

''' #### Display Name
Note that the Extension is automatically converted to a DisplayNameExtension
'''
display_name = pac.get_extension('N') # display name has name 'N'
print(display_name) 

'''#### TREX'''

trexes = pac.get_extension_of_type('TREX')
trex_extension = trexes[0] # there could be multiple trexes. In this example there is only one, though
trex = trex_extension.trex
v = trex.get_segment('WEIGHT')
print(f'WEIGHT = {v.value}')



''' 
### Create a PAC-ID with Extensions

#### Create PAC-ID
'''
from labfreed import PAC_ID, IDSegment  # noqa: E402
from labfreed.well_known_keys.labfreed.well_known_keys import WellKnownKeys  # noqa: E402

pac = PAC_ID(issuer='METTORIUS.COM', identifier=[IDSegment(key=WellKnownKeys.SERIAL, value='1234')])
pac_str = pac.to_url()
print(pac_str)


''' 
#### Create a TREX 
TREX can conveniently be created from a python dictionary.
Note that utility types for Quantity (number with unit) and table are needed
'''
from datetime import datetime  # noqa: E402
from labfreed.trex.python_convenience import pyTREX  # noqa: E402
from labfreed.trex.python_convenience import DataTable  # noqa: E402
from labfreed.trex.python_convenience import Quantity  # noqa: E402

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
''''''

''' 
#### Combine PAC-ID and TREX and serialize
'''
from labfreed.well_known_extensions import TREX_Extension  # noqa: E402
pac.extensions = [TREX_Extension(name='MYTREX', trex=trex)]
pac_str = pac.to_url()
print(pac_str)



'''
## PAC-ID Resolver
'''
from labfreed import PAC_ID_Resolver, load_cit  # noqa: E402
# Get a CIT
dir = os.path.join(os.getcwd(), 'examples')
p = os.path.join(dir, 'cit_mine.yaml')       
cit = load_cit(p)

# validate the CIT
cit.is_valid
cit.print_validation_messages(target=target)

''''''
# get a second cit
p = os.path.join(dir, 'coupling-information-table')       
cit2 = load_cit(p)
cit2.origin = 'MY_COMPANY'

''''''
# resolve a pac id
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MS/X3511/CAS:7732-18-5'
service_groups = PAC_ID_Resolver(cits=[cit, cit2]).resolve(pac_str)
for sg in service_groups:
    sg.update_states()
    sg.print()
    

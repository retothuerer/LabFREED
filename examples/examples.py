# import built ins
import os

target = 'console'
''' 
### Parse a simple PAC-ID 
'''
# Parse the PAC-ID
from labfreed.pac_id import PAC_ID

pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234'
try:
    pac = PAC_ID.from_url(pac_str)
except:
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
from labfreed.qr import save_qr_with_markers

save_qr_with_markers(pac_str, fmt='png')

'''
### PAC-CAT
PAC-CAT defines a (optional) way how the identifier is structured.
PAC_ID.from_url() automatically converts to PAC-CAT if possible.
'''
from labfreed.pac_cat import PAC_CAT
pac_str = 'HTTPS://PAC.METTORIUS.COM/-DR/XQ908756/-MD/bal500/@1234'
pac = PAC_ID.from_url(pac_str)
if isinstance(pac, PAC_CAT):
    categories = pac.categories 
    pac.print_categories()

'''if the PAC-ID has no valid categories no PAC-CAT will be created'''
pac_str = 'HTTPS://PAC.METTORIUS.COM/XQ908756/bal500/@1234' # not valid PAC-CAT
pac = PAC_ID.from_url(pac_str) 

'''You can also use getattr'''
categories = getattr(pac, 'categories', None) 

''' or catch the Attribute Error'''
try:
    categories = pac.categories
except AttributeError as e:
    pass
    

    


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
from labfreed.pac_id import PAC_ID, IDSegment
from labfreed.well_known_keys.labfreed.well_known_keys import WellKnownKeys

pac = PAC_ID(issuer='METTORIUS.COM', identifier=[IDSegment(key=WellKnownKeys.SERIAL, value='1234')])
pac_str = pac.to_url()
print(pac_str)


''' 
#### Create a TREX 
TREX can conveniently be created from a python dictionary.
Note that utility types for Quantity (number with unit) and table are needed
'''
from datetime import datetime
from labfreed.trex import TREX
from labfreed.trex.python_convenience.pyTREX import pyTREX
from labfreed.trex.python_convenience.data_table import DataTable
from labfreed.trex.python_convenience.quantity import Quantity

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
from labfreed.well_known_extensions import TREX_Extension
pac.extensions = [TREX_Extension(name='MYTREX', trex=trex)]
pac_str = pac.to_url()
print(pac_str)



'''
## PAC-ID Resolver
'''
from labfreed.pac_id_resolver import PAC_ID_Resolver, load_cit
# Get a CIT
dir = os.path.dirname(__file__)
p = os.path.join(dir, 'cit_mine.yaml')       
cit = load_cit(p)

# validate the CIT
cit.is_valid
cit.print_validation_messages(target=target)

''''''
# resolve a pac id
service_groups = PAC_ID_Resolver(cits=[cit]).resolve(pac)
for sg in service_groups:
    sg.update_states()
    sg.print()
    

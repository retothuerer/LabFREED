from datetime import datetime
from typing import Annotated

# Parse a PAC ID
from labfreed.PAC_ID.data_model import PACID, IDSegment
from labfreed.parse import PAC_Parser, PACID_With_Extensions
from utility_types import Quantity
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234'
pac = PAC_Parser().parse_pac_id(pac_str)

## Check validity
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/bal500/@1234'
pac = PAC_Parser().parse_pac_id(pac_str)
is_valid = pac.is_valid()
print('PAC-ID is valid: {is_valid}')

# Show recommendations
pac.print_validation_messages()




## Parse a PAC-ID with extensions
pac_str = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234*N$N/WM633OV3E5DGJW2BEG0PDM1EA7*SUM$TREX/WEIGHT$GRM:67.89'
pac = PAC_Parser().parse_pac_with_extensions(pac_str)

# Display Name
display_names = pac.get_extension('N')
print(f'\nDisplay names: {display_names}')

# TREX
from labfreed.TREX.data_model import TREX, ColumnHeader, TREX_Table, TableRow
trexes = pac.get_extension_of_type('TREX')
trex:TREX = trexes[0]
v = trex.get_segment('WEIGHT').to_python_type()




## Create a PAC-ID
from labfreed.utilities.well_known_keys import WellKnownKeys
pac = PACID(issuer='METTORIUS:COM', identifier=[IDSegment(key=WellKnownKeys.SERIAL, value='1234')])
pac_str = pac.serialize()
pac_str = pac.serialize()
print(pac_str)




# create a TREX
from labfreed.TREX.data_model import TREX, DateSegment, NumericSegment, BoolSegment, AlphanumericSegment, TextSegment, BinarySegment

trex = TREX(name_='DEMO-TREX')

trex.segments.append(DateSegment(key='START',value='20240505T1204'))
trex.segments.append(DateSegment(key='STOP', value=datetime(year=2024,month=5,day=5,hour=13,minute=6)) )

trex.segments.append(NumericSegment(key='TEMP',type='KEL', value=10.15) )
trex.segments.append(BoolSegment(key='OK', value=False) )
trex.segments.append(AlphanumericSegment(key='COMMENT', value='FOO') )
trex.segments.append(TextSegment(key='COMMENT2', value='🐯') )
trex.segments.append(TextSegment(key='COMMENT2', value='BAR') )

# if the sting is already in base36 you have to be explicit
from labfreed.utilities.base36 import base36
trex.segments.append(TextSegment(key='COMMENT3', value=base36('1URIOQ7')) )

# table
table = TREX_Table(key='TABLE', 
                   column_headers=[
                                    ColumnHeader(key='COL1', type='HUR'), 
                                    ColumnHeader(key='COL2', type='T.A'),
                                    ColumnHeader(key='COL3', type='T.D'),
                                    ColumnHeader(key='COL4', type='T.B')
                                    ],
                   data=[
                       TableRow()
                   ])
trex.segments.append(table)

if trex.is_valid():
    print(trex.data)
else:
    trex.print_validation_messages()
    

p = PACID_With_Extensions(pac_id=pac, extensions=[trex])
print(p.serialize())





# for convenience a TREX can be created from a dict
trex2 = TREX(name_='DEMO-TREX2')
trex2.update(   
                    {
                        'STOP': datetime(year=2024,month=5,day=5,hour=13,minute=6),
                        'TEMP': Quantity(value=10.15, unit_name='meter', unit_symbol='m'),
                        'OK':False,
                        'COMMENT': 'FOO',
                        'COMMENT2':'🐯'
                    }
)

d = trex2.dict()



    






from datetime import datetime
from labfreed.TREX.data_model import TREX
from labfreed.TREX.parse import TREX_Parser
from labfreed.DisplayNameExtension.DisplayNameExtension import DisplayNames


from labfreed.PAC_CAT.data_model import *
from labfreed.utilities.base36 import base36
from labfreed.utilities.utility_types import DataTable, Quantity, Unit


if __name__ == "__main__":
    
    table = DataTable(['DURATION', 'DATE', 'OK', 'COMMENT'])
    table.append([Quantity(value=1, unit=Unit(symbol='h', name='hour')), datetime.now(), True, 'FOO'])
    table.append([1.1,  datetime.now(), True, 'BAR'])
    table.append([1.3,  datetime.now(), False, 'BLUBB'])
    table.append([1.3,  datetime.now(), 1, 'BLUBB'])

    
    trex = TREX(name_='TEST')
    trex.update({'TABLE': table})
    trex.update({'TEMP': Quantity(value=100, unit=Unit(name='kelvin', symbol='K'))})
    trex.print_validation_messages()
    print(trex)
    
    d = trex.dict()
    
    
    
    
    parser = TREX_Parser()
    
    trex_str = 'A$T.T:ABCDE'
    trex = parser.parse_trex_str(trex_str, name="A")
    
    valid_strs = [
        'TIME$HUR:-25E2',
        'TIME$HUR:-25E-2',
        'TIME$HUR:-25.12E2',
        'TIME$HUR:-25.12E-2'
    ]
    for trex_str in valid_strs:
        trex = parser.parse_trex_str(trex_str, name="A")
        assert trex.data == trex_str
        v = trex.get_segment('TIME').to_python_type()
    
    # extension_interpreters = {
    #         'TREX': TREX,
    #         'N': DisplayNames
    # }

    # pacid_str = 'HTTPS://PAC.METTORIUS.COM/-DR/AB378/-MD/B-500/1235/-MS/AB/X:88/WWW/-MS/240:11/BB*E4BLEW6R5EVD7XMGHG11*A$HUR:25+B$CEL:99*BLUBB$TREX/A$HUR:25+B$CEL:99'
    # pac = PAC_Parser(extension_interpreters).parse_pac(pacid_str)
    # a=1
    

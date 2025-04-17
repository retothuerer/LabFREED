
from datetime import datetime
import os

import yaml
from labfreed.IO.parse_pac import PAC_Parser
from labfreed.pac_id_resolver import PAC_ID_Resolver, load_cit
from labfreed.trex import TREX
from labfreed.display_name_extension.display_name_extension import DisplayName
from labfreed.pac_cat import PAC_CAT
from labfreed.utilities.base36 import base36
from labfreed.python_convenience.utility_types import DataTable, Quantity, Unit

from labfreed.IO.generate_qr import save_qr_with_markers

if __name__ == "__main__":
    
    
    pac = PAC_Parser().parse('HTTPS://PAC.METTORIUS.COM/-DR/MADFGAI/-MD/ABCG/ACG/PC:1234')  

    cat = PAC_CAT.from_pac_id(pac.pac_id)
    cat.identifier
    jsn = cat.model_dump_json(indent=2)
    print(jsn)
    
    '''
    ## PAC-ID Resolver
    '''
    # Get a CIT
    dir = os.path.dirname(__file__)
    p = os.path.join(dir, 'cit_mine.yaml')       
    cit = load_cit(p)

    # validate the CIT
    cit.is_valid()
    cit.print_validation_messages()

    
    pac_with_ext = PAC_Parser().parse('HTTPS://PAC.METTORIUS.COM/-DR/maDFGAI/-MD/ABaCmG/ACG/PC:1234*SUM$TREX/A$T.B:X+B$T.X:ABC', suppress_errors=True)
    pac_with_ext.print_validation_messages()
    
    
    pac = PAC_Parser().parse('HTTPS://PAC.METTORIUS.COM/-DR/MADFGAI/-MD/ABCG/ACG/PC:1234')
    
    dir = os.path.dirname(__file__)
    p = os.path.join(dir, 'cit_mine.yaml')       
    cit = load_cit(p)

    services = PAC_ID_Resolver(cits=[cit]).resolve(pac)
    

    cat = PAC_CAT.from_pac_id(pac.pac_id)
    cat.identifier
    jsn = cat.model_dump_json(indent=2)
    print(jsn)
    
    
    
    save_qr_with_markers('HTTPS://PAC.METTORIUS.COM/-MD/ABCG/ACG') 
    
    
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
    
    d = trex.to_dict()
    
    
    
        
    trex_str = 'A$T.T:ABCDE'
    trex = TREX.deserialize(trex_str, name="A")
    
    valid_strs = [
        'TIME$HUR:-25E2',
        'TIME$HUR:-25E-2',
        'TIME$HUR:-25.12E2',
        'TIME$HUR:-25.12E-2'
    ]
    for trex_str in valid_strs:
        trex = TREX.deserialize(trex_str, name="A")
        assert trex.data == trex_str
        v = trex.get_segment('TIME').to_python_type()
    
    # extension_interpreters = {
    #         'TREX': TREX,
    #         'N': DisplayNames
    # }

    # pacid_str = 'HTTPS://PAC.METTORIUS.COM/-DR/AB378/-MD/B-500/1235/-MS/AB/X:88/WWW/-MS/240:11/BB*E4BLEW6R5EVD7XMGHG11*A$HUR:25+B$CEL:99*BLUBB$TREX/A$HUR:25+B$CEL:99'
    # pac = PAC_Parser(extension_interpreters).parse_pac(pacid_str)
    # a=1
    


from labfreed.TREXExtension.data_model import TREX
from labfreed.DisplayNameExtension.DisplayNameExtension import DisplayNames


from labfreed.PAC_CAT.data_model import *


if __name__ == "__main__":
    # extension_interpreters = {
    #         'TREX': TREX,
    #         'N': DisplayNames
    # }

    # pacid_str = 'HTTPS://PAC.METTORIUS.COM/-DR/AB378/-MD/B-500/1235/-MS/AB/X:88/WWW/-MS/240:11/BB*E4BLEW6R5EVD7XMGHG11*A$HUR:25+B$CEL:99*BLUBB$TREX/A$HUR:25+B$CEL:99'
    # pac = PAC_Parser(extension_interpreters).parse_pac(pacid_str)
    # a=1
    
    
    md = Material_Device(serial_number='123', model_number='aa')
    md2 = Material_Device(**{'21': '123', '240': 'aa'})
    1
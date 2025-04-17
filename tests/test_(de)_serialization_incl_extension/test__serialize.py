from pytest import fixture
from labfreed.pac_id import PACID, IDSegment
from labfreed.pac_id.extension import UnknownExtension
from labfreed.IO.parse_pac import PACID_With_Extensions


pac_id = PACID(issuer = 'mettorius.com',
            identifier = [  IDSegment(value='-DR'), 
                            IDSegment(value='999'),
                            IDSegment(value="-MD"),
                            IDSegment(key='240', value='1'),
                            IDSegment(key='21', value='2')
                        ]
          ) 

extensions= [
    UnknownExtension(name_= 'N', type_= 'T.T', data_= 'DATA'),
    UnknownExtension(name_= 'SUM', type_= 'TREX', data_= 'DATA'),
    UnknownExtension(name_= 'FOO', type_= 'T', data_= 'DATA'),
    UnknownExtension(name_= 'BAR', type_= 'T2', data_= 'DATA')
]

@fixture
def pac_with_ext():
    return PACID_With_Extensions(pac_id=pac_id, extensions=extensions)


def test_url_serialization(pac_with_ext):
    url = pac_with_ext.serialize( use_short_notation=False, uppercase_only=True)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*N$T.T/DATA*SUM$TREX/DATA*FOO$T/DATA*BAR$T2/DATA'
    
def test_url_serialization_short_notation_for_N_and_SUM_extensions(pac_with_ext):
    url = pac_with_ext.serialize(use_short_notation=True, uppercase_only=True)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*DATA*DATA*FOO$T/DATA*BAR$T2/DATA'
    
def test_url_serialization_short_notation_for_N_extensions(pac_with_ext):
    pac_with_ext.extensions = [extensions[i] for i in (0,2,3)]
    url = pac_with_ext.serialize( use_short_notation=True, uppercase_only=True)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*DATA*FOO$T/DATA*BAR$T2/DATA'
    
def test_url_serialization_short_notation_stop_implying_when_specific_extension(pac_with_ext):
    pac_with_ext.extensions = [extensions[i] for i in (2,3)]
    url = pac_with_ext.serialize( use_short_notation=True, uppercase_only=True)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*FOO$T/DATA*BAR$T2/DATA'
    
    

    
    
    
    

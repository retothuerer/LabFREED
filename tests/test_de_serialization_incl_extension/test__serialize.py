from pytest import fixture
from labfreed.pac_id import PAC_ID, IDSegment
from labfreed.pac_id.extension import Extension




extensions= [
    Extension(name= 'N', type= 'TEXT', data= 'DATA'),
    Extension(name= 'SUM', type= 'TREX', data= 'DATA'),
    Extension(name= 'FOO', type= 'T', data= 'DATA'),
    Extension(name= 'BAR', type= 'T2', data= 'DATA')
]

@fixture
def pac() -> PAC_ID:
    pac_id = PAC_ID(issuer = 'mettorius.com',
            identifier = [  IDSegment(value='-DR'), 
                            IDSegment(value='999'),
                            IDSegment(value="-MD"),
                            IDSegment(key='240', value='1'),
                            IDSegment(key='21', value='2')
                        ]
          ) 
    return pac_id

    
def test_extension_type_and_name_are_optional(pac):
    e = Extension(name= None, type= None, data= 'DATA-QWERTAUAZD')
    assert e.is_valid
    w = e.validation_messages()
    assert len(w) > 0 # recommendation to add name and type
    
    pac.extensions = [e]
    url = pac.to_url( use_short_notation=False, uppercase_only=True)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*DATA-QWERTAUAZD'
    
    

def test_url_serialization(pac):
    pac.extensions = extensions
    url = pac.to_url( use_short_notation=False, uppercase_only=True)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*N$TEXT/DATA*SUM$TREX/DATA*FOO$T/DATA*BAR$T2/DATA'
    
def test_url_serialization_short_notation_for_N_and_SUM_extensions(pac):
    pac.extensions = extensions
    url = pac.to_url(use_short_notation=True, uppercase_only=True)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*DATA*DATA*FOO$T/DATA*BAR$T2/DATA'
    
def test_url_serialization_short_notation_for_N_extensions(pac):
    pac.extensions = [extensions[i] for i in (0,2,3)]
    url = pac.to_url( use_short_notation=True, uppercase_only=True)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*DATA*FOO$T/DATA*BAR$T2/DATA'
    
def test_url_serialization_short_notation_stop_implying_when_specific_extension(pac):
    pac.extensions = [extensions[i] for i in (2,3)]
    url = pac.to_url( use_short_notation=True, uppercase_only=True)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*FOO$T/DATA*BAR$T2/DATA'
    
    

    
    
    
    

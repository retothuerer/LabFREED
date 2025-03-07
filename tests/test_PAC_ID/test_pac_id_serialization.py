from labfreed.PAC_ID.data_model import PACID, Identifier, Category, IDSegment, UnknownExtension, PACID_With_Extensions
from labfreed.PAC_ID.serialize import PAC_Serializer

serializer = PAC_Serializer()

pac_id = PACID(issuer = 'mettorius.com',
            identifier = Identifier.from_categories( [
                                            Category(key="-DR", 
                                                    segments=[
                                                        IDSegment(value='999'),
                                                        ]
                                                    ),
                                            Category(key="-MD", 
                                                    segments=[
                                                        IDSegment(key='240', value='1'),
                                                        IDSegment(key='21', value='2')
                                                        ]
                                                    ) 
                                        ])
)
extensions= [
    UnknownExtension(name_= 'FOO', type_= 'T', data_= 'DATA'),
    UnknownExtension(name_= 'BAR', type_= 'T2', data_= 'DATA')
]


def test_url_serialization():
    url = serializer.to_url(pac_id, extensions)
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2*FOO$T/DATA*BAR$T2/DATA'
    
    

    
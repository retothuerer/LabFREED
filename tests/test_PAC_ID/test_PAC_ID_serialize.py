from labfreed.PAC_ID.data_model import PACID, IDSegment

pac_id = PACID(issuer = 'METTORIUS.COM',
            identifier = [  IDSegment(value='-DR'), 
                            IDSegment(value='999'),
                            IDSegment(value="-MD"),
                            IDSegment(key='240', value='1'),
                            IDSegment(key='21', value='2')
                        ]
          ) 

 
def test_url_serialization():
    url = pac_id.serialize()
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2'
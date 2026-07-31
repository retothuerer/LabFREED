from labfreed.pac_id import PAC_ID, IDSegment

pac_id = PAC_ID(issuer = 'METTORIUS.COM',
            identifier = [  IDSegment(value='-DR'), 
                            IDSegment(value='999'),
                            IDSegment(value="-MD"),
                            IDSegment(key='240', value='1'),
                            IDSegment(key='21', value='2')
                        ]
          ) 

 
def test_url_serialization():
    url = pac_id.to_url()
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2'


def test_to_dict_includes_as_url_matching_to_url():
    d = pac_id.to_dict()
    assert d['as_url'] == pac_id.to_url()
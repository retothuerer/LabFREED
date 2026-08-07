import pytest

from labfreed.pac_id import PAC_ID, IDSegment
from labfreed.pac_id.extension import Extension

pac_id = PAC_ID(issuer = 'METTORIUS.COM',
            identifier = [  IDSegment(value='-DR'),
                            IDSegment(value='999'),
                            IDSegment(value="-MD"),
                            IDSegment(key='240', value='1'),
                            IDSegment(key='21', value='2')
                        ]
          )

pac_id_with_extension = PAC_ID(issuer = 'METTORIUS.COM',
            identifier = [  IDSegment(value='-DR'),
                            IDSegment(value='999'),
                        ],
            extensions = [ Extension.create(name='N', type='TEXT', data='ABC') ]
          )


def test_url_serialization():
    url = pac_id.to_url()
    assert url == 'HTTPS://PAC.METTORIUS.COM/-DR/999/-MD/240:1/21:2'


def test_to_dict_includes_serialized_as_url_including_extensions_matching_to_url():
    d = pac_id_with_extension.to_dict()
    assert d['serialized_as_url_including_extensions'] == pac_id_with_extension.to_url()


def test_to_dict_includes_serialized_as_url_without_extensions_matching_to_url_without_extensions():
    d = pac_id_with_extension.to_dict()
    assert d['serialized_as_url_without_extensions'] == pac_id_with_extension.to_url(include_extensions=False)

from labfreed.pac_cat.pac_cat import PAC_CAT



valid_base = "HTTPS://PAC.METTORIUS.COM/"
valid_standard_segments = "-MD/240:B-800/21:12345"
valid_dummy_extension = "DUMMY$MYTYPE/DUMMYDATA"


def from_url(url):
    return PAC_CAT.from_url(url, suppress_validation_errors=True)

    
def test_identifier_with_keys_is_preserved_exactly_when_deserialize_and_serialize_in_sequence():
    url_in = valid_base + "-MD/240:B-800/21:12345"
    pac = from_url(url_in)
    assert type(pac) is PAC_CAT
    url = pac.to_url()
    assert url == url_in


def test_identifier_without_keys_is_preserved_exactly_when_deserialize_and_serialize_in_sequence():
    url_in = valid_base + "-MD/B-800/12345"
    pac = from_url(url_in)
    assert type(pac) is PAC_CAT
    url = pac.to_url()
    assert url == url_in
    
    
def test_force_short_notation():
    url_in = valid_base + "-MD/240:B-800/21:12345"
    pac = from_url(url_in)
    assert type(pac) is PAC_CAT
    url = pac.to_url(use_short_notation=True)
    assert url == valid_base + "-MD/B-800/12345"
    

def test_force_long_notation():
    url_in = valid_base + "-MD/B-800/12345"
    pac = from_url(url_in)
    assert type(pac) is PAC_CAT
    url = pac.to_url(use_short_notation=False)
    assert url == valid_base + "-MD/240:B-800/21:12345"
  
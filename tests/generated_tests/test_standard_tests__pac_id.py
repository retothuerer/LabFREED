
import pytest # noqa: F401
from labfreed.pac_id import PAC_ID, IDSegment # noqa: F401

def from_url(url):
    return PAC_ID.from_url(url, suppress_validation_errors=True)

class Test_pac_id:

    def test_standard_base_gives_correct_issuer(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MD/240:B-800/21:12345')
        assert pac.is_valid
        assert pac.issuer == 'METTORIUS.COM'

    def test_pac_can_be_missing_from_domain(self):
        pac = from_url('METTORIUS.COM/-MD/240:B-800/21:12345')
        assert pac.is_valid
        assert pac.issuer == 'METTORIUS.COM'

    def test_issuer_must_be_valid_domain(self):
        pac = from_url('HTTPS://METTORIUS/-MD/240:B-800/21:12345')
        assert not pac.is_valid

    def test_pac_must_have_at_least_one_segment(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/')
        assert not pac.is_valid

    def test_identifier_named_segment(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/KEY:VAL')
        segs = pac.identifier
        assert len(segs) == 1
        assert segs[0].key == 'KEY'
        assert segs[0].value == 'VAL'

    def test_identifier_unnamed_segment(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/VAL')
        segs = pac.identifier
        assert len(segs) == 1
        assert not segs[0].key
        assert segs[0].value == 'VAL'

    def test_identifier_combination_of_named_and_unnamed_segments(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/KEY0:VAL0/VAL1/KEY2:VAL2')
        segs = pac.identifier
        assert len(segs) == 3
        assert segs[0].key == 'KEY0'
        assert segs[0].value == 'VAL0'
        assert not segs[1].key
        assert segs[1].value == 'VAL1'
        assert segs[2].key == 'KEY2'
        assert segs[2].value == 'VAL2'

    def test_keys_must_be_unique(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/KEY:VAL/KEY:ANOTHERVAL/KEY:VAL/KEY2:ANOTHERVAL')
        assert len(pac.warnings()) > 0

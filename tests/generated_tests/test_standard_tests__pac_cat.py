
import pytest # noqa: F401
from labfreed.pac_id import PAC_ID, IDSegment # noqa: F401

def from_url(url):
    return PAC_ID.from_url(url, suppress_validation_errors=True)

class Test_pac_cat:

    def test_valid_category_md(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MD/ABC/1234')
        assert pac.is_valid
        assert pac.to_url(use_short_notation=False) == 'HTTPS://PAC.METTORIUS.COM/-MD/240:ABC/21:1234'
        assert pac.to_url(use_short_notation=True) == 'HTTPS://PAC.METTORIUS.COM/-MD/ABC/1234'

    def test_basic_valid_category(self):
        """Single valid category segment"""
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-DM/21:VAL')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 1
        assert cats[0].key == '-DM'
        assert len(cats[0].segments) == 1
        assert cats[0].segments[0].key == '21'
        assert cats[0].segments[0].value == 'VAL'

    def test_category_with_multiple_segments(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MX/KEY0:VAL0/VAL1/KEY2:VAL2')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 1
        assert cats[0].key == '-MX'
        assert len(cats[0].segments) == 3
        assert cats[0].segments[0].key == 'KEY0'
        assert cats[0].segments[0].value == 'VAL0'
        assert cats[0].segments[1].key is None
        assert cats[0].segments[1].value == 'VAL1'
        assert cats[0].segments[2].key == 'KEY2'
        assert cats[0].segments[2].value == 'VAL2'

    def test_two_categories(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-DX/KEY:VAL/-MX/KEY:VAL')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 2
        assert cats[0].key == '-DX'
        assert len(cats[0].segments) == 1
        assert cats[0].segments[0].key == 'KEY'
        assert cats[0].segments[0].value == 'VAL'
        assert cats[1].key == '-MX'
        assert len(cats[1].segments) == 1
        assert cats[1].segments[0].key == 'KEY'
        assert cats[1].segments[0].value == 'VAL'

    def test_three_categories(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-DX/KEY0:VAL0/-MX/KEY1:VAL1/-CAT/KEY2:VAL2')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 3
        assert cats[0].key == '-DX'
        assert len(cats[0].segments) == 1
        assert cats[0].segments[0].key == 'KEY0'
        assert cats[0].segments[0].value == 'VAL0'
        assert cats[1].key == '-MX'
        assert len(cats[1].segments) == 1
        assert cats[1].segments[0].key == 'KEY1'
        assert cats[1].segments[0].value == 'VAL1'
        assert cats[2].key == '-CAT'
        assert len(cats[2].segments) == 1
        assert cats[2].segments[0].key == 'KEY2'
        assert cats[2].segments[0].value == 'VAL2'

    def test_implied_segments_of_MD_category(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MD/0/1')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 1
        assert cats[0].key == '-MD'
        assert len(cats[0].segments) == 2
        assert cats[0].segments[0].key == '240'
        assert cats[0].segments[0].value == '0'
        assert cats[0].segments[1].key == '21'
        assert cats[0].segments[1].value == '1'

    def test_implied_segments_of_MS_category(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MS/0/1/2/3/4')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 1
        assert cats[0].key == '-MS'
        assert len(cats[0].segments) == 5
        assert cats[0].segments[0].key == '240'
        assert cats[0].segments[0].value == '0'
        assert cats[0].segments[1].key == '10'
        assert cats[0].segments[1].value == '1'
        assert cats[0].segments[2].key == '20'
        assert cats[0].segments[2].value == '2'
        assert cats[0].segments[3].key == '21'
        assert cats[0].segments[3].value == '3'
        assert cats[0].segments[4].key == '250'
        assert cats[0].segments[4].value == '4'

    def test_implied_segments_of_MC_category(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MC/0/1/2/3/4')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 1
        assert cats[0].key == '-MC'
        assert len(cats[0].segments) == 5
        assert cats[0].segments[0].key == '240'
        assert cats[0].segments[0].value == '0'
        assert cats[0].segments[1].key == '10'
        assert cats[0].segments[1].value == '1'
        assert cats[0].segments[2].key == '20'
        assert cats[0].segments[2].value == '2'
        assert cats[0].segments[3].key == '21'
        assert cats[0].segments[3].value == '3'
        assert cats[0].segments[4].key == '250'
        assert cats[0].segments[4].value == '4'

    def test_implied_segments_of_MM_category(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MM/0/1/2/3/4')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 1
        assert cats[0].key == '-MM'
        assert len(cats[0].segments) == 5
        assert cats[0].segments[0].key == '240'
        assert cats[0].segments[0].value == '0'
        assert cats[0].segments[1].key == '10'
        assert cats[0].segments[1].value == '1'
        assert cats[0].segments[2].key == '20'
        assert cats[0].segments[2].value == '2'
        assert cats[0].segments[3].key == '21'
        assert cats[0].segments[3].value == '3'
        assert cats[0].segments[4].key == '250'
        assert cats[0].segments[4].value == '4'

    def test_stop_implying_segments_after_an_explicit_one_is_found(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MS/0/1/KEY:2/3/4')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 1
        assert cats[0].key == '-MS'
        assert len(cats[0].segments) == 5
        assert cats[0].segments[0].key == '240'
        assert cats[0].segments[0].value == '0'
        assert cats[0].segments[1].key == '10'
        assert cats[0].segments[1].value == '1'
        assert cats[0].segments[2].key == 'KEY'
        assert cats[0].segments[2].value == '2'
        assert cats[0].segments[3].key is None
        assert cats[0].segments[3].value == '3'
        assert cats[0].segments[4].key is None
        assert cats[0].segments[4].value == '4'

    def test_more_segments_than_implicit_keys(self):
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MD/IMPLIED1/IMPLIED2/ADDITIONAL')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 1
        assert cats[0].key == '-MD'
        assert len(cats[0].segments) == 3
        assert cats[0].segments[0].key == '240'
        assert cats[0].segments[0].value == 'IMPLIED1'
        assert cats[0].segments[1].key == '21'
        assert cats[0].segments[1].value == 'IMPLIED2'
        assert cats[0].segments[2].key is None
        assert cats[0].segments[2].value == 'ADDITIONAL'

    def test_mandatory_fields_of_MD_category_invalid(self):
        """MD category missing required fields, should be invalid"""
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MD/KEY:VAL')
        assert not pac.is_valid

    def test_mandatory_fields_of_MD_category_valid(self):
        """Valid MD category with required serial and model number"""
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MD/21:1234/KEY:VAL/240:BAL500')
        assert pac.is_valid
        cats = pac.categories
        assert len(cats) == 1
        assert cats[0].key == '-MD'
        assert len(cats[0].segments) == 3
        assert cats[0].segments[0].key == '240'
        assert cats[0].segments[0].value == 'BAL500'
        assert cats[0].segments[1].key == '21'
        assert cats[0].segments[1].value == '1234'
        assert cats[0].segments[2].key == 'KEY'
        assert cats[0].segments[2].value == 'VAL'

    def test_keys_can_repeat_accross_categories(self):
        """Same key used in two categories is allowed"""
        pac = from_url('HTTPS://PAC.METTORIUS.COM/-MX/KEY:VAL/-MY/KEY:VAL')
        assert pac.is_valid

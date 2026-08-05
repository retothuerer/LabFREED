import pytest

from labfreed.pac_cat import PAC_CAT
from labfreed.pac_id import IDSegment, PAC_ID
from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo


def _pac_cat(url_tail):
    return PAC_CAT.from_url(f'HTTPS://PAC.METTORIUS.COM/{url_tail}', suppress_validation_errors=True)


def _plain_pac_id():
    return PAC_ID(issuer='METTORIUS.COM', identifier=[IDSegment(value='-DR'), IDSegment(value='999')])


def test_main_category_is_none_for_a_plain_non_pac_cat_id():
    assert PacInfo(pac_id=_plain_pac_id()).main_category is None


def test_main_category_is_the_first_category_of_a_pac_cat():
    pac_info = PacInfo(pac_id=_pac_cat('-MD/240:BAL500/21:12345'))
    assert pac_info.main_category.key == '-MD'


def test_is_item_serialized_is_none_for_a_plain_non_pac_cat_id():
    assert PacInfo(pac_id=_plain_pac_id()).is_item_serialized is None


def test_is_item_serialized_true_when_category_has_a_serial_number():
    pac_info = PacInfo(pac_id=_pac_cat('-MD/240:BAL500/21:12345'))
    assert pac_info.is_item_serialized is True


def test_is_item_serialized_false_at_product_level_with_no_serial_number():
    pac_info = PacInfo(pac_id=_pac_cat('-MD/240:BAL500'))
    assert pac_info.is_item_serialized is False

'''
PAC_ID.__eq__/__hash__ scoped to (issuer, identifier), extensions excluded.

Compares the serialized `to_url(include_extensions=False)` string rather than
comparing `self.identifier`/IDSegment objects directly - see design-choices.md
("PAC_ID.__eq__/__hash__ scoped to (issuer, identifier), extensions excluded")
for why: LabFREED_BaseModel._validation_messages (a PrivateAttr storing
source_id=id(self)) participates in pydantic's default equality, so two
structurally-identical IDSegments that each independently accumulated even an
identical validation message would otherwise compare unequal.

Deliberately cross-type: a PAC_CAT and a PAC_ID with the same issuer+identifier
compare equal, since PAC_CAT is an interpretive view over PAC_ID.identifier, not
a different entity, and parsing already opportunistically upgrades to PAC_CAT.
'''
import pytest

from labfreed.pac_id import PAC_ID, IDSegment, Extension
from labfreed.pac_cat import PAC_CAT


def _pac(issuer="METTORIUS.COM", value="FOO", extension=None):
    extensions = [extension] if extension else []
    return PAC_ID(issuer=issuer, identifier=[IDSegment(value=value)], extensions=extensions)


def test_same_issuer_and_identifier_are_equal_regardless_of_extensions():
    a = _pac()
    b = _pac(extension=Extension(name="N", type="TEXT", data="ABC"))
    assert a == b
    assert hash(a) == hash(b)


def test_different_extensions_are_still_equal():
    a = _pac(extension=Extension(name="N", type="TEXT", data="ABC"))
    b = _pac(extension=Extension(name="N", type="TEXT", data="XYZ"))
    assert a == b
    assert hash(a) == hash(b)


def test_different_issuer_is_not_equal():
    a = _pac(issuer="METTORIUS.COM")
    b = _pac(issuer="ACME.COM")
    assert a != b


def test_different_identifier_is_not_equal():
    a = _pac(value="FOO")
    b = _pac(value="BAR")
    assert a != b


def test_equality_survives_independently_accumulated_identical_validation_messages():
    ''' Regression test for the id(self)-in-equality landmine (see module docstring):
    triggering the same RECOMMENDATION-level "key not in WellKnownKeys" message
    independently on each side must not make two otherwise-identical PAC_IDs unequal. '''
    a = PAC_ID(issuer="METTORIUS.COM", identifier=[IDSegment(key="NOT_WELL_KNOWN", value="FOO")])
    b = PAC_ID(issuer="METTORIUS.COM", identifier=[IDSegment(key="NOT_WELL_KNOWN", value="FOO")])
    assert a._get_nested_validation_messages()  # sanity: something was actually recorded
    assert a == b
    assert hash(a) == hash(b)


def test_pac_cat_and_pac_id_with_same_issuer_and_identifier_are_equal():
    identifier = [IDSegment(key="240", value="X67678"), IDSegment(key="10", value="9999")]
    pac_id = PAC_ID(issuer="METTORIUS.COM", identifier=identifier)
    pac_cat = PAC_CAT(issuer="METTORIUS.COM", identifier=identifier)
    assert pac_id == pac_cat
    assert hash(pac_id) == hash(pac_cat)


def test_comparison_with_a_non_pac_id_is_not_equal_and_does_not_crash():
    a = _pac()
    assert a != "METTORIUS.COM/FOO"
    assert a != object()
    assert a is not None

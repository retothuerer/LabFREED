import pytest

from labfreed.labfreed_infrastructure import LabFREED_ValidationError
from labfreed.pac_id import PAC_ID, IDSegment


valid_base = "HTTPS://PAC.METTORIUS.COM/"
valid_standard_segments = "-MD/240:B-800/21:12345"
valid_dummy_extension = "DUMMY$MYTYPE/DUMMYDATA"


def from_url(url):
    return PAC_ID.from_url(url, suppress_validation_errors=True, try_pac_cat=False)


# Issuer
def test_standard_base_gives_correct_issuer():
    pac = from_url("HTTPS://PAC.METTORIUS.COM/" + valid_standard_segments)
    assert pac.is_valid
    assert pac.issuer == "METTORIUS.COM"
       
     
def test_pac_can_be_missing_from_domain():
    pac = from_url("METTORIUS.COM/" + valid_standard_segments)
    assert pac.issuer == "METTORIUS.COM"
    
def test_issuer_must_be_valid_domain():
    pac = from_url("HTTPS://METTORIUS/" + valid_standard_segments)
    assert not pac.is_valid
        
    

# Identifier Segments
def test_pac_must_have_at_least_one_segment():
    pac = from_url(valid_base + "")
    assert not pac.is_valid
          
def test_identifier_named_segment():
    pac = from_url(valid_base + "KEY:VAL")
    seg: IDSegment = pac.identifier[0]
    assert seg.key == "KEY"
    assert seg.value == "VAL"
    
def test_identifier_unnamed_segment():
    pac = from_url(valid_base + "VAL")
    seg: IDSegment = pac.identifier[0]
    assert not seg.key
    assert seg.value == "VAL"
     
def test_identifier_combination_of_named_and_unnamed_segments():
    pac = from_url(valid_base + "KEY0:VAL0/VAL1/KEY2:VAL2")
    seg: IDSegment = pac.identifier[0]
    assert seg.key == 'KEY0'
    assert seg.value == "VAL0"
    
    seg: IDSegment = pac.identifier[1]
    assert not seg.key
    assert seg.value == "VAL1"
    
    seg: IDSegment = pac.identifier[2]
    assert seg.key == 'KEY2'
    assert seg.value == "VAL2"
      
def test_keys_must_be_unique():
    pac = from_url(valid_base + "KEY:VAL/KEY:ANOTHERVAL/KEY:VAL/KEY2:ANOTHERVAL")
    assert len(pac.warnings()) > 0


def test_extra_colon_splits_on_the_first_one_but_is_invalid():
    '''Only the first ':' separates key and value, so a segment with a second
    colon (e.g. a non-basic-format timestamp) parses deterministically rather
    than crashing the parser -- but id segment key/value MUST NOT contain ':',
    so the result is correctly flagged invalid, not silently accepted.'''
    pac = from_url(valid_base + "TS:20250101T1200:00")
    seg: IDSegment = pac.identifier[0]
    assert seg.key == "TS"
    assert seg.value == "20250101T1200:00"
    assert not pac.is_valid


def test_repeated_slash_produces_an_invalid_empty_segment():
    '''A repeated '/' in the identifier produces a segment with an empty value,
    which carries no information and must be flagged - unlike a single trailing
    '/' (see below), which is tolerated.'''
    pac = from_url(valid_base + "KEY:VAL//KEY2:VAL2")
    assert not pac.is_valid
    assert any('must not be empty' in m.msg for m in pac.validation_messages())


def test_repeated_slash_still_raises_without_suppression():
    with pytest.raises(LabFREED_ValidationError):
        PAC_ID.from_url(valid_base + "KEY:VAL//KEY2:VAL2", try_pac_cat=False)


def test_doubled_trailing_slash_is_also_invalid():
    '''A trailing '/' is only tolerated once - a doubled trailing '/' still
    produces a genuinely empty segment and is left as an ERROR.'''
    pac = from_url(valid_base + "KEY:VAL//")
    assert not pac.is_valid
    assert any('must not be empty' in m.msg for m in pac.validation_messages())


def test_single_trailing_slash_is_stripped_and_only_warns():
    '''A single trailing '/' produces no id segment at all, so there is nothing
    to flag as empty. It's still not good practice (see design-choices.md
    "trailing `/` is tolerated"), so it's flagged as a WARNING rather than
    silently accepted - but it does not make the PAC-ID invalid, and does not
    raise even without suppress_validation_errors.'''
    pac = PAC_ID.from_url(valid_base + "KEY:VAL/", try_pac_cat=False)
    assert pac.is_valid
    assert len(pac.identifier) == 1
    assert pac.identifier[0].value == "VAL"
    assert any('trailing' in m.msg for m in pac.warnings())


def test_has_derivation_segments():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1")
    assert pac.has_derivation_segments()


def test_has_derivation_segments_is_false_without_one():
    pac = from_url(valid_base + valid_standard_segments)
    assert not pac.has_derivation_segments()


def test_get_derivation_namespaces_single():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1")
    assert pac.get_derivation_namespaces() == ['ACMELABS.COM']


def test_get_derivation_namespaces_chained():
    '''Chained derivation by multiple parties -- note each namespace segment needs
    its own '/', unlike the spec's README example ('.../250:1+PARTNERLAB.ORG/...'),
    which merges the second '+' into the previous segment's value instead of
    starting a new one; that looks like a typo in the spec text.'''
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1/+PARTNERLAB.ORG/TESTPORTION:A")
    assert pac.get_derivation_namespaces() == ['ACMELABS.COM', 'PARTNERLAB.ORG']


def test_get_derivation_namespaces_empty_without_derivation():
    pac = from_url(valid_base + valid_standard_segments)
    assert pac.get_derivation_namespaces() == []


def test_get_non_derived_pac_id_strips_namespace_segments_and_extensions():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1*N$TEXT/ABC")
    base = pac.get_non_derived_pac_id()
    assert base.to_url() == "HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876"
    assert base.extensions == []
    assert not base.has_derivation_segments()


def test_get_non_derived_pac_id_without_derivation_keeps_extensions():
    '''Without derivation, this PAC-ID already *is* the non-derived one -- its
    extensions describe this same entity and stay valid, so they must not be
    dropped (unlike the derivation case, where they describe the child entity).'''
    pac = from_url(valid_base + valid_standard_segments + "*N$TEXT/ABC")
    base = pac.get_non_derived_pac_id()
    assert base is pac
    assert base.extensions == pac.extensions


def test_get_parent_pac_id_strips_only_the_last_marker():
    '''Unlike get_non_derived_pac_id (which strips back to the root), a chained
    derivation's immediate parent still carries the earlier marker(s).'''
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876"
                    "/+ACMELABS.COM/250:1/+PARTNERLAB.ORG/TESTPORTION:A")
    parent = pac.get_parent_pac_id()
    assert parent.to_url() == "HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1"
    assert parent.get_derivation_namespaces() == ['ACMELABS.COM']
    assert parent.to_url() != pac.get_non_derived_pac_id().to_url()


def test_get_parent_pac_id_matches_root_without_chaining():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1")
    assert pac.get_parent_pac_id().to_url() == pac.get_non_derived_pac_id().to_url()

def test_get_parent_pac_id_without_marker_drops_last_segment():
    '''No `+<namespace>` marker doesn't mean there's no parent: the issuing party's
    own derivation needs no marker (see PAC-ID spec, "Issuing derived PAC-ID"s, and
    server.py's _get_derivation_parent_id). ".../-MD/240:B-800/21:12345"'s parent is
    ".../-MD/240:B-800" -- dropping the last id segment, same as the marker case,
    drops extensions too since they describe the child entity, not the parent.'''
    pac = from_url(valid_base + valid_standard_segments + "*N$TEXT/ABC")
    parent = pac.get_parent_pac_id()
    assert parent.to_url() == valid_base + "-MD/240:B-800"
    assert parent.extensions == []


def test_get_parent_pac_id_returns_none_for_bare_category_plus_one_field():
    '''Dropping the last segment here would leave a bare, field-less category key
    ("-MD" alone) -- not a meaningful narrower entity, so this identifier already
    is its own parent, same as the true no-parent case.'''
    pac = from_url(valid_base + "-MD/240:B-800" + "*N$TEXT/ABC")
    parent = pac.get_parent_pac_id()
    assert parent is None


def test_get_parent_pac_id_drops_extensions_when_derived():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1*N$TEXT/ABC")
    parent = pac.get_parent_pac_id()
    assert parent.extensions == []


def test_derive_appends_marker_and_segments():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876")
    derived = pac.derive("ACMELABS.COM", IDSegment(key="250", value="1"))
    assert derived.to_url() == "HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1"
    assert derived.get_derivation_namespaces() == ["ACMELABS.COM"]


def test_derive_drops_parents_extensions():
    '''The derived PAC-ID refers to a different entity than its parent, so the
    parent's extensions (which describe the parent) must not carry over.'''
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876*N$TEXT/ABC")
    derived = pac.derive("ACMELABS.COM", IDSegment(key="250", value="1"))
    assert derived.extensions == []


def test_derive_round_trips_via_get_parent_pac_id():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876")
    derived = pac.derive("ACMELABS.COM", IDSegment(key="250", value="1"))
    assert derived.get_parent_pac_id().to_url() == pac.to_url()


def test_is_derived_from_direct_parent():
    parent = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876")
    child = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1")
    assert child.is_derived_from(parent)


def test_is_derived_from_grandparent():
    root = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876")
    grandchild = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876"
                           "/+ACMELABS.COM/250:1/+PARTNERLAB.ORG/TESTPORTION:A")
    assert grandchild.is_derived_from(root)


def test_is_derived_from_is_false_for_self():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1")
    assert not pac.is_derived_from(pac)


def test_is_derived_from_is_false_for_unrelated_pac_id():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1")
    other = from_url(valid_base + valid_standard_segments)
    assert not pac.is_derived_from(other)


def test_is_derived_from_is_false_for_different_issuer():
    pac = from_url("HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1")
    other = from_url("HTTPS://PAC.ACMELABS.COM/-MS/240:AMYLASE/10:AB9876/21:9876")
    assert not pac.is_derived_from(other)


def test_combined_issuer_and_identifier_length_recommendation():
    '''Combined length of issuer and identifier SHOULD NOT exceed 100 characters,
    even if the 256 character MUST-limit on identifier alone isn't hit.'''
    long_issuer = "HTTPS://PAC." + "A" * 40 + ".COM/"
    pac = from_url(long_issuer + "X" * 70)
    assert pac.is_valid  # still valid, just not recommended
    assert len(pac.warnings()) > 0
        

        
        

    

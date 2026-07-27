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


def test_empty_id_segment_value_is_invalid():
    '''A double or trailing '/' in the identifier produces a segment with an
    empty value, which carries no information and must be flagged.'''
    pac = from_url(valid_base + "KEY:VAL/")
    assert not pac.is_valid


def test_combined_issuer_and_identifier_length_recommendation():
    '''Combined length of issuer and identifier SHOULD NOT exceed 100 characters,
    even if the 256 character MUST-limit on identifier alone isn't hit.'''
    long_issuer = "HTTPS://PAC." + "A" * 40 + ".COM/"
    pac = from_url(long_issuer + "X" * 70)
    assert pac.is_valid  # still valid, just not recommended
    assert len(pac.warnings()) > 0
        

        
        

    

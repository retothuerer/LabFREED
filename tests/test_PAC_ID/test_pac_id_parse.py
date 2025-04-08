import pytest
from labfreed.PAC_ID.data_model import IDSegment
from labfreed.parse import PAC_Parser


valid_base = "HTTPS://PAC.METTORIUS.COM/"
valid_standard_segments = "-MD/240:B-800/21:12345"
valid_dummy_extension = "DUMMY$MYTYPE/DUMMYDATA"


parser = PAC_Parser()



# Issuer
def test_standard_base_gives_correct_issuer():
    pac = parser.parse_pac_with_extensions("HTTPS://PAC.METTORIUS.COM/" + valid_standard_segments)
    assert pac.pac_id.issuer == "METTORIUS.COM"
       
def test_pac_can_be_missing_from_domain():
    pac = parser.parse_pac_with_extensions("HTTPS://METTORIUS.COM/" + valid_standard_segments)
    assert pac.pac_id.issuer == "METTORIUS.COM"
     
def test_pac_can_be_missing_from_domain():
    pac = parser.parse_pac_with_extensions("METTORIUS.COM/" + valid_standard_segments)
    assert pac.pac_id.issuer == "METTORIUS.COM"
    
def test_issuer_must_be_valid_domain():
    with pytest.raises(Exception):
        pac = parser.parse_pac_with_extensions("HTTPS://METTORIUS/" + valid_standard_segments)
        
        
        
        

# Identifier Segments
def test_pac_must_have_at_least_one_segment():
    with pytest.raises(Exception):
        pac = parser.parse_pac_with_extensions(valid_base = "").pac_id
          
def test_identifier_named_segment():
    pac = parser.parse_pac_with_extensions(valid_base + "KEY:VAL")
    seg: IDSegment = pac.pac_id.identifier[0]
    assert seg.key == "KEY"
    assert seg.value == "VAL"
    
def test_identifier_unnamed_segment():
    pac = parser.parse_pac_with_extensions(valid_base + "VAL")
    seg: IDSegment = pac.pac_id.identifier[0]
    assert not seg.key
    assert seg.value == "VAL"
     
def test_identifier_combination_of_named_and_unnamed_segments():
    pac = parser.parse_pac_with_extensions(valid_base + "KEY0:VAL0/VAL1/KEY2:VAL2")
    pac = pac.pac_id
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
    pac = parser.parse_pac_with_extensions(valid_base + "KEY:VAL/KEY:ANOTHERVAL/KEY:VAL/KEY2:ANOTHERVAL")
    assert len(pac.pac_id.get_warnings()) > 0
        
def test_keys_can_repeat_accross_categories():
    pac = parser.parse_pac_with_extensions(valid_base + "-MD/KEY:VAL/-MS/KEY:VAL")
    assert True # made it here without exception > it's fine
        
        

    

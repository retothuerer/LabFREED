import logging
import pytest
from labfreed.pac_cat import Category, PAC_CAT
from labfreed.pac_id import IDSegment
from labfreed.IO.parse_pac import PAC_Parser
from labfreed.labfreed_infrastructure import LabFREED_ValidationError

logging.basicConfig(level=logging.INFO)  # or DEBUG if needed
logger = logging.getLogger(__name__)


valid_base = "HTTPS://PAC.METTORIUS.COM/"
valid_standard_segments = "-MD/240:B-800/21:12345"
valid_dummy_extension = "DUMMY$MYTYPE/DUMMYDATA"


parser = PAC_Parser(use_pac_cat=True, suppress_validation_errors=True)


# Identifier Segments Categories (Recommendation)
def test_basic_valid_category():
    pac = parser.parse(valid_base + "-DM/21:VAL")
    cat: Category = pac.pac_id.categories[0]
    assert cat.key == '-DM'
    assert cat.segments[0].key == '21'
    assert cat.segments[0].value == 'VAL'
    
def test_if_no_category_is_specified_default_to_unnamed_category():
    pac = parser.parse(valid_base + "KEY:VAL")
    cat: Category = pac.pac_id.categories[0]
    assert cat.key is None
    assert cat.segments[0].key == 'KEY'
    assert cat.segments[0].value == 'VAL'
    
def test_missing_dash_in_category_name_is_interpreted_as_unnamed_segment():
    pac = parser.parse(valid_base + "DM/21:VAL")
    cat: Category = pac.pac_id.categories[0]
    assert cat.key is None
    assert cat.segments[0].value == 'DM'
    
def test_category_with_multiple_segments():
    pac = parser.parse(valid_base + "-MX/KEY0:VAL0/VAL1/KEY2:VAL2")
    cat: Category = pac.pac_id.categories[0]
    assert cat.key == '-MX'
    
    seg: IDSegment = cat.segments[0]
    assert seg.key == 'KEY0'
    assert seg.value == "VAL0"
    
    seg: IDSegment = cat.segments[1]
    assert not seg.key
    assert seg.value == "VAL1"
    
    seg: IDSegment = cat.segments[2]
    assert seg.key == 'KEY2'
    assert seg.value == "VAL2"
      
def test_two_categories():
    pac = parser.parse(valid_base + "-DX/KEY:VAL/-MX/KEY:VAL")
    cat: Category = pac.pac_id.categories[0]
    assert cat.key == '-DX'
    assert cat.segments[0].key == 'KEY'
    assert cat.segments[0].value == 'VAL'
    
    cat: Category = pac.pac_id.categories[1]
    assert cat.key == '-MX'
    assert cat.segments[0].key == 'KEY'
    assert cat.segments[0].value == 'VAL'
     
def test_three_categories():
    pac = parser.parse(valid_base + "-DX/KEY0:VAL0/-MX/KEY1:VAL1/-CAT/KEY2:VAL2")
    pac = pac.pac_id
    cat: Category = pac.categories[0]
    assert cat.key == '-DX'
    assert cat.segments[0].key == 'KEY0'
    assert cat.segments[0].value == 'VAL0'
    
    cat: Category = pac.categories[1]
    assert cat.key == '-MX'
    assert cat.segments[0].key == 'KEY1'
    assert cat.segments[0].value == 'VAL1'
    
    cat: Category = pac.categories[2]
    assert cat.key == '-CAT'
    assert cat.segments[0].key == 'KEY2'
    assert cat.segments[0].value == 'VAL2'
    
def test_implied_segments_of_MD_category():
    pac = parser.parse(valid_base + "-MD/0/1")
    cat: Category = pac.pac_id.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '21'
    
def test_implied_segments_of_MS_category():
    pac = parser.parse(valid_base + "-MS/0/1/2/3/4")
    cat: Category = pac.pac_id.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == '20'
    assert cat.segments[3].key == '21'
    assert cat.segments[4].key == '250'
    
def test_implied_segments_of_MC_category():
    pac = parser.parse(valid_base + "-MC/0/1/2/3/4")
    cat: Category = pac.pac_id.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == '20'
    assert cat.segments[3].key == '21'
    assert cat.segments[4].key == '250'
    
def test_implied_segments_of_MM_category():
    pac = parser.parse(valid_base + "-MM/0/1/2/3/4")
    cat: Category = pac.pac_id.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == '20'
    assert cat.segments[3].key == '21'
    assert cat.segments[4].key == '250'
    
def test_stop_implying_segments_after_an_explicit_one_is_found():
    pac = parser.parse(valid_base + "-MS/0/1/KEY:2/3/4")
    cat: Category = pac.pac_id.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == 'KEY'
    assert cat.segments[3].key == None
    assert cat.segments[4].key == None
    
def test_more_segments_than_implicit_keys():
    pac = parser.parse(valid_base + "-MD/IMPLIED1/IMPLIED2/ADDITIONAL")
    cat: Category = pac.pac_id.categories[0]
    assert cat.segments[2].key == None
    
    
    
    
    
def test_mandatory_fields_of_MD_category():
    pac = parser.parse(valid_base + "-MD/KEY:VAL")
    assert not pac.is_valid
    
    pac:PAC_CAT = parser.parse(valid_base + "-MD/21:1234/KEY:VAL/240:BAL500").pac_id
    assert pac.get_category('-MD').serial_number == '1234'
    assert pac.get_category('-MD').model_number == 'BAL500'
    
    
def test_keys_can_repeat_accross_categories():
    pac = parser.parse(valid_base + "-MX/KEY:VAL/-MY/KEY:VAL")
    assert pac.is_valid # made it here without exception > it's fine
    

    

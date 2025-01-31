import pytest
from PAC_ID.data_model import Category, Extension, IDSegment
from PAC_ID.parse import PAC_Parser


valid_base = "HTTPS://PAC.METTORIUS.COM/"
valid_standard_segments = "-MD/240:B-800/21:12345"
valid_dummy_extension = "DUMMY$MYTYPE/DUMMYDATA"


parser = PAC_Parser()



# Issuer
def test_standard_base_gives_correct_issuer():
    pac = parser.parse_pac("HTTPS://PAC.METTORIUS.COM/" + valid_standard_segments)
    assert pac.issuer == "METTORIUS.COM"
       
def test_pac_can_be_missing_from_domain():
    pac = parser.parse_pac("HTTPS://METTORIUS.COM/" + valid_standard_segments)
    assert pac.issuer == "METTORIUS.COM"
     
def test_pac_can_be_missing_from_domain():
    pac = parser.parse_pac("METTORIUS.COM/" + valid_standard_segments)
    assert pac.issuer == "METTORIUS.COM"
    
def test_issuer_must_be_valid_domain():
    with pytest.raises(Exception):
        pac = parser.parse_pac("HTTPS://METTORIUS/" + valid_standard_segments)
        
        
        
        

# Identifier Segments
def test_pac_must_have_at_least_one_segment():
    with pytest.raises(Exception):
        pac = parser.parse_pac(valid_base = "")
          
def test_identifier_named_segment():
    pac = parser.parse_pac(valid_base + "key:val")
    seg: IDSegment = pac.identifier.segments[0]
    assert seg.key == "key"
    assert seg.value == "val"
    
def test_identifier_unnamed_segment():
    pac = parser.parse_pac(valid_base + "val")
    seg: IDSegment = pac.identifier.segments[0]
    assert not seg.key
    assert seg.value == "val"
     
def test_identifier_combination_of_named_and_unnamed_segments():
    pac = parser.parse_pac(valid_base + "key0:val0/val1/key2:val2")
    seg: IDSegment = pac.identifier.segments[0]
    assert seg.key == 'key0'
    assert seg.value == "val0"
    
    seg: IDSegment = pac.identifier.segments[1]
    assert not seg.key
    assert seg.value == "val1"
    
    seg: IDSegment = pac.identifier.segments[2]
    assert seg.key == 'key2'
    assert seg.value == "val2"
      
def test_keys_must_be_unique():
    with pytest.raises(Exception):
        pac = parser.parse_pac(valid_base + "key:value/key:anothervalue/key2:value/key2:anothervalue")
        
def test_keys_can_repeat_accross_categories():
    pac = parser.parse_pac(valid_base + "-MD/key:val/-MS/key:val")
    assert True # made it here without exception > it's fine
        
        


# Identifier Segments Categories (Recommendation)
def test_basic_valid_category():
    pac = parser.parse_pac(valid_base + "-MD/key:val")
    cat: Category = pac.identifier.categories[0]
    assert cat.key == '-MD'
    assert cat.segments[0].key == 'key'
    assert cat.segments[0].value == 'val'
    
def test_if_no_category_is_specified_default_to_unnamed_category():
    pac = parser.parse_pac(valid_base + "key:val")
    cat: Category = pac.identifier.categories[0]
    assert cat.key == None
    assert cat.segments[0].key == 'key'
    assert cat.segments[0].value == 'val'
    
def test_missing_dash_in_category_name_is_interpreted_as_unnamed_segment():
    pac = parser.parse_pac(valid_base + "MD/key:val")
    cat: Category = pac.identifier.categories[0]
    assert cat.key == None
    assert cat.segments[0].value == 'MD'
    
def test_category_with_multiple_segments():
    pac = parser.parse_pac(valid_base + "-MD/key0:val0/val1/key2:val2")
    cat: Category = pac.identifier.categories[0]
    assert cat.key == '-MD'
    
    seg: IDSegment = cat.segments[0]
    assert seg.key == 'key0'
    assert seg.value == "val0"
    
    seg: IDSegment = cat.segments[1]
    assert not seg.key
    assert seg.value == "val1"
    
    seg: IDSegment = cat.segments[2]
    assert seg.key == 'key2'
    assert seg.value == "val2"
      
def test_two_categories():
    pac = parser.parse_pac(valid_base + "-DR/key:val/-MD/key:val")
    cat: Category = pac.identifier.categories[0]
    assert cat.key == '-DR'
    assert cat.segments[0].key == 'key'
    assert cat.segments[0].value == 'val'
    
    cat: Category = pac.identifier.categories[1]
    assert cat.key == '-MD'
    assert cat.segments[0].key == 'key'
    assert cat.segments[0].value == 'val'
     
def test_three_categories():
    pac = parser.parse_pac(valid_base + "-DR/key0:val0/-MD/key1:val1/-CAT/key2:val2")
    cat: Category = pac.identifier.categories[0]
    assert cat.key == '-DR'
    assert cat.segments[0].key == 'key0'
    assert cat.segments[0].value == 'val0'
    
    cat: Category = pac.identifier.categories[1]
    assert cat.key == '-MD'
    assert cat.segments[0].key == 'key1'
    assert cat.segments[0].value == 'val1'
    
    cat: Category = pac.identifier.categories[2]
    assert cat.key == '-CAT'
    assert cat.segments[0].key == 'key2'
    assert cat.segments[0].value == 'val2'
    
def test_implied_segments_of_MD_category():
    pac = parser.parse_pac(valid_base + "-MD/0/1")
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '21'
    
def test_implied_segments_of_MS_category():
    pac = parser.parse_pac(valid_base + "-MS/0/1/2/3/4")
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == '20'
    assert cat.segments[3].key == '21'
    assert cat.segments[4].key == '250'
    
def test_implied_segments_of_MC_category():
    pac = parser.parse_pac(valid_base + "-MC/0/1/2/3/4")
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == '20'
    assert cat.segments[3].key == '21'
    assert cat.segments[4].key == '250'
    
def test_implied_segments_of_MM_category():
    pac = parser.parse_pac(valid_base + "-MM/0/1/2/3/4")
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == '20'
    assert cat.segments[3].key == '21'
    assert cat.segments[4].key == '250'
    
def test_stop_implying_segments_after_an_explicit_one_is_found():
    pac = parser.parse_pac(valid_base + "-MS/0/1/key:2/3/4")
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == 'key'
    assert cat.segments[3].key == None
    assert cat.segments[4].key == None
    
def test_more_segments_than_implicit_keys():
    pac = parser.parse_pac(valid_base + "-MD/implied1/implied2/additional")
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[2].key == None
    
    
    
# Extensions
def test_valid_extensions():
    pac = parser.parse_pac(valid_base + valid_standard_segments + "*name1$t1/data1*name2$t2/data2")
    ext: Extension = pac.extensions[0]
    assert ext.name == 'name1'
    assert ext.type == 't1'
    assert ext.data == 'data1'
    
    ext: Extension = pac.extensions[1]
    assert ext.name == 'name2'
    assert ext.type == 't2'
    assert ext.data == 'data2'

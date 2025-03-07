import pytest
from labfreed.PAC_ID.data_model import Category, Extension, IDSegment
from labfreed.PAC_ID.parse import PAC_Parser


valid_base = "HTTPS://PAC.METTORIUS.COM/"
valid_standard_segments = "-MD/240:B-800/21:12345"
valid_dummy_extension = "DUMMY$MYTYPE/DUMMYDATA"


parser = PAC_Parser()



# Issuer
def test_standard_base_gives_correct_issuer():
    pac = parser.parse_pac_url("HTTPS://PAC.METTORIUS.COM/" + valid_standard_segments).pac_id
    assert pac.issuer == "METTORIUS.COM"
       
def test_pac_can_be_missing_from_domain():
    pac = parser.parse_pac_url("HTTPS://METTORIUS.COM/" + valid_standard_segments).pac_id
    assert pac.issuer == "METTORIUS.COM"
     
def test_pac_can_be_missing_from_domain():
    pac = parser.parse_pac_url("METTORIUS.COM/" + valid_standard_segments).pac_id
    assert pac.issuer == "METTORIUS.COM"
    
def test_issuer_must_be_valid_domain():
    with pytest.raises(Exception):
        pac = parser.parse_pac_url("HTTPS://METTORIUS/" + valid_standard_segments).pac_id
        
        
        
        

# Identifier Segments
def test_pac_must_have_at_least_one_segment():
    with pytest.raises(Exception):
        pac = parser.parse_pac_url(valid_base = "").pac_id
          
def test_identifier_named_segment():
    pac = parser.parse_pac_url(valid_base + "KEY:VAL").pac_id
    seg: IDSegment = pac.identifier.segments[0]
    assert seg.key == "KEY"
    assert seg.value == "VAL"
    
def test_identifier_unnamed_segment():
    pac = parser.parse_pac_url(valid_base + "VAL").pac_id
    seg: IDSegment = pac.identifier.segments[0]
    assert not seg.key
    assert seg.value == "VAL"
     
def test_identifier_combination_of_named_and_unnamed_segments():
    pac = parser.parse_pac_url(valid_base + "KEY0:VAL0/VAL1/KEY2:VAL2").pac_id
    seg: IDSegment = pac.identifier.segments[0]
    assert seg.key == 'KEY0'
    assert seg.value == "VAL0"
    
    seg: IDSegment = pac.identifier.segments[1]
    assert not seg.key
    assert seg.value == "VAL1"
    
    seg: IDSegment = pac.identifier.segments[2]
    assert seg.key == 'KEY2'
    assert seg.value == "VAL2"
      
def test_keys_must_be_unique():
    with pytest.raises(Exception):
        pac = parser.parse_pac_url(valid_base + "KEY:VAL/KEY:ANOTHERVAL/KEY:VAL/KEY2:ANOTHERVAL").pac_id
        
def test_keys_can_repeat_accross_categories():
    pac = parser.parse_pac_url(valid_base + "-MD/KEY:VAL/-MS/KEY:VAL").pac_id
    assert True # made it here without exception > it's fine
        
        


# Identifier Segments Categories (Recommendation)
def test_basic_valid_category():
    pac = parser.parse_pac_url(valid_base + "-MD/KEY:VAL").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.key == '-MD'
    assert cat.segments[0].key == 'KEY'
    assert cat.segments[0].value == 'VAL'
    
def test_if_no_category_is_specified_default_to_unnamed_category():
    pac = parser.parse_pac_url(valid_base + "KEY:VAL").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.key == None
    assert cat.segments[0].key == 'KEY'
    assert cat.segments[0].value == 'VAL'
    
def test_missing_dash_in_category_name_is_interpreted_as_unnamed_segment():
    pac = parser.parse_pac_url(valid_base + "MD/KEY:VAL").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.key == None
    assert cat.segments[0].value == 'MD'
    
def test_category_with_multiple_segments():
    pac = parser.parse_pac_url(valid_base + "-MD/KEY0:VAL0/VAL1/KEY2:VAL2").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.key == '-MD'
    
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
    pac = parser.parse_pac_url(valid_base + "-DR/KEY:VAL/-MD/KEY:VAL").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.key == '-DR'
    assert cat.segments[0].key == 'KEY'
    assert cat.segments[0].value == 'VAL'
    
    cat: Category = pac.identifier.categories[1]
    assert cat.key == '-MD'
    assert cat.segments[0].key == 'KEY'
    assert cat.segments[0].value == 'VAL'
     
def test_three_categories():
    pac = parser.parse_pac_url(valid_base + "-DR/KEY0:VAL0/-MD/KEY1:VAL1/-CAT/KEY2:VAL2").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.key == '-DR'
    assert cat.segments[0].key == 'KEY0'
    assert cat.segments[0].value == 'VAL0'
    
    cat: Category = pac.identifier.categories[1]
    assert cat.key == '-MD'
    assert cat.segments[0].key == 'KEY1'
    assert cat.segments[0].value == 'VAL1'
    
    cat: Category = pac.identifier.categories[2]
    assert cat.key == '-CAT'
    assert cat.segments[0].key == 'KEY2'
    assert cat.segments[0].value == 'VAL2'
    
def test_implied_segments_of_MD_category():
    pac = parser.parse_pac_url(valid_base + "-MD/0/1").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '21'
    
def test_implied_segments_of_MS_category():
    pac = parser.parse_pac_url(valid_base + "-MS/0/1/2/3/4").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == '20'
    assert cat.segments[3].key == '21'
    assert cat.segments[4].key == '250'
    
def test_implied_segments_of_MC_category():
    pac = parser.parse_pac_url(valid_base + "-MC/0/1/2/3/4").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == '20'
    assert cat.segments[3].key == '21'
    assert cat.segments[4].key == '250'
    
def test_implied_segments_of_MM_category():
    pac = parser.parse_pac_url(valid_base + "-MM/0/1/2/3/4").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == '20'
    assert cat.segments[3].key == '21'
    assert cat.segments[4].key == '250'
    
def test_stop_implying_segments_after_an_explicit_one_is_found():
    pac = parser.parse_pac_url(valid_base + "-MS/0/1/KEY:2/3/4").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[0].key == '240'
    assert cat.segments[1].key == '10'
    assert cat.segments[2].key == 'KEY'
    assert cat.segments[3].key == None
    assert cat.segments[4].key == None
    
def test_more_segments_than_implicit_keys():
    pac = parser.parse_pac_url(valid_base + "-MD/IMPLIED1/IMPLIED2/ADDITIONAL").pac_id
    cat: Category = pac.identifier.categories[0]
    assert cat.segments[2].key == None
    
    
    
# Extensions
def test_valid_extensions():
    extensions = parser.parse_pac_url(valid_base + valid_standard_segments + "*name1$t1/data1*name2$t2/data2").extensions
    ext: Extension = extensions[0]
    assert ext.name == 'name1'
    assert ext.type == 't1'
    assert ext.data == 'data1'
    
    ext: Extension = extensions[1]
    assert ext.name == 'name2'
    assert ext.type == 't2'
    assert ext.data == 'data2'
    
def test_known_extension_types_are_parsed():
    class ExtensionMockType(Extension):
        @property
        def name(self)->str:
            return 'name__foo'
        
        @property
        def type(self)->str:
            return 'type__foo'
        
        @property
        def data(self)->str:
            return 'data__foo'
        
        @staticmethod
        def from_spec_fields(name, type, data):
            return ExtensionMockType()
        
    extension_interpreters = {
            'KNOWN_EXTENSION': ExtensionMockType,
    }  
    parser_with_known_extension = PAC_Parser(extension_interpreters)
    extensions = parser_with_known_extension.parse_pac_url(valid_base + valid_standard_segments + "*name1$KNOWN_EXTENSION/data1").extensions
    ext: Extension = extensions[0]
    assert isinstance(ext, ExtensionMockType)
    assert ext.name == 'name__foo'
    assert ext.type == 'type__foo'
    assert ext.data == 'data__foo'
    
    
def test_imply_display_name_and_summary_extension():
    extensions = parser.parse_pac_url(valid_base + valid_standard_segments + "*data1*data2").extensions
    ext: Extension = extensions[0]
    assert ext.name == 'N'
    assert ext.type == 'N'
    
    ext: Extension = extensions[1]
    assert ext.name == 'SUM'
    assert ext.type == 'TREX'
    
def test_stop_imply_extensions_after_explicit():
    with pytest.raises(Exception):
        _ = parser.parse_pac_url(valid_base + valid_standard_segments + "*N$T/data1*data2").extensions
        

def test_extension_parsing():
    s = '*NAME$MYFORMAT/AUGDSJGTZFRDGJHDSFRTZGHJAAUTZSGADT*NAME$ANOTHERFORMAT/BLUBBER'
    extensions = parser.parse_extensions(s)
    ext: Extension = extensions[0]
    assert ext.name == 'NAME'
    assert ext.type == 'MYFORMAT'
    assert ext.data == 'AUGDSJGTZFRDGJHDSFRTZGHJAAUTZSGADT'
    
    ext: Extension = extensions[1]
    assert ext.name == 'NAME'
    assert ext.type == 'ANOTHERFORMAT'
    assert ext.data == 'BLUBBER'

    

import pytest
from labfreed.PAC_ID.extensions import Extension
from labfreed.parse import PAC_Parser


valid_base = "HTTPS://PAC.METTORIUS.COM/"
valid_standard_segments = "-MD/240:B-800/21:12345"
valid_dummy_extension = "DUMMY$MYTYPE/DUMMYDATA"

parser = PAC_Parser()

# Extensions
def test_valid_extensions():
    pac = parser.parse_pac_with_extensions(valid_base + valid_standard_segments + "*name1$t1/data1*name2$t2/data2")
    extensions = pac.extensions
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
    pac = parser_with_known_extension.parse_pac_with_extensions(valid_base + valid_standard_segments + "*name1$KNOWN_EXTENSION/data1")
    extensions= pac.extensions
    ext: Extension = extensions[0]
    assert isinstance(ext, ExtensionMockType)
    assert ext.name == 'name__foo'
    assert ext.type == 'type__foo'
    assert ext.data == 'data__foo'
    
    
def test_imply_display_name_and_summary_extension():
    pac = parser.parse_pac_with_extensions(valid_base + valid_standard_segments + "*data1*data2")
    extensions = pac.extensions
    ext: Extension = extensions[0]
    assert ext.name == 'N'
    assert ext.type == 'N'
    
    ext: Extension = extensions[1]
    assert ext.name == 'SUM'
    assert ext.type == 'TREX'
    
def test_stop_imply_extensions_after_explicit():
    with pytest.raises(Exception):
        pac = parser.parse_pac_with_extensions(valid_base + valid_standard_segments + "*N$T/data1*data2")
        pac.extensions
        

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

    

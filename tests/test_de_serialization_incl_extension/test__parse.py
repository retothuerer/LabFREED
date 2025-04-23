from typing import Self
import pytest
from labfreed.pac_id import PAC_ID
from labfreed.pac_id.extension import ExtensionBase, Extension
from labfreed.well_known_extensions.display_name_extension import DisplayNameExtension
from labfreed.well_known_extensions.trex_extension import TREX_Extension


valid_base = "HTTPS://PAC.METTORIUS.COM/"
valid_standard_segments = "-MD/240:B-800/21:12345"
valid_dummy_extension = "DUMMY$MYTYPE/DUMMYDATA"

def from_url(url):
    return PAC_ID.from_url(url, suppress_validation_errors=True)

# Extensions
def test_valid_extensions():
    pac = from_url(valid_base + valid_standard_segments + "*name1$t1/data1*name2$t2/data2")
    extensions = pac.extensions
    ext: Extension = extensions[0]
    assert ext.name == 'name1'
    assert ext.type == 't1'
    assert ext.data == 'data1'
    
    ext: Extension = extensions[1]
    assert ext.name == 'name2'
    assert ext.type == 't2'
    assert ext.data == 'data2'
    
    
def test_known_extensions_are_interpreted():
    class ExtensionMockType(ExtensionBase):
        
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
        def create(*,name, type, data) -> Self:
            return ExtensionMockType()
        
        @staticmethod
        def from_extension(ext:Extension):
            e = ExtensionMockType()
            return e
        
    extension_interpreters = {
            'KNOWN_EXTENSION': ExtensionMockType,
    }  
    url = valid_base + valid_standard_segments + "*name1$KNOWN_EXTENSION/data1"
    pac = PAC_ID.from_url(url, suppress_validation_errors=True, extension_interpreters=extension_interpreters)
   
    extensions= pac.extensions
    ext: Extension = extensions[0]
    assert isinstance(ext, ExtensionMockType)

  
def test_display_name_and_summary_are_known_extension_types():
    pac = from_url(valid_base + valid_standard_segments + "*N$N/ABC*SUM$TREX/A$T.A:A")
    extensions= pac.extensions
    assert isinstance(extensions[0], DisplayNameExtension)
    assert isinstance(extensions[1], TREX_Extension)
    
   
    
def test_imply_display_name_and_summary_extension():
    pac = from_url(valid_base + valid_standard_segments + "*ABC*S1$T.A:ABC")
    extensions = pac.extensions
    ext: Extension = extensions[0]
    assert ext.name == 'N'
    assert ext.type == 'N'
    
    ext: Extension = extensions[1]
    assert ext.name == 'SUM'
    assert ext.type == 'TREX'
    
def test_stop_imply_extensions_after_explicit():
    with pytest.raises(Exception):
        pac = from_url(valid_base + valid_standard_segments + "*N$T/data1*data2")
        pac.extensions
        

def test_extension_parsing():
    s = '*NAME$MYFORMAT/AUGDSJGTZFRDGJHDSFRTZGHJAAUTZSGADT*NAME$ANOTHERFORMAT/BLUBBER'
    extensions = from_url('HTTPS://PAC.METTORIUS.COM/A' + s).extensions  
    ext: Extension = extensions[0]
    assert ext.name == 'NAME'
    assert ext.type == 'MYFORMAT'
    assert ext.data == 'AUGDSJGTZFRDGJHDSFRTZGHJAAUTZSGADT'
    
    ext: Extension = extensions[1]
    assert ext.name == 'NAME'
    assert ext.type == 'ANOTHERFORMAT'
    assert ext.data == 'BLUBBER'

    

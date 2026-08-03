'''
PAC_CAT.main_category and PAC_CAT.processor - convenience accessors on top of
`.categories`.

`main_category` is the first category in the identifier - the one the PAC-ID actually
refers to (PAC-CAT: "the first category is always what the PAC-ID actually refers to").

`processor` is the second category in the identifier, if present - PAC-CAT's "second
category identifying what system generated/manages this record". It is purely
positional: whichever category sits there counts, regardless of type (usually `-PS`/
`-PX`, or a `-MD` instrument - devices can act as processors too; their material
characteristic just takes precedence in categorization). A PAC-ID with only one
category has no processor, even if that lone category would otherwise look
processor-shaped.
'''
import pytest

from labfreed.pac_cat import PAC_CAT, Processor_Software, Processor_Misc, Material_Device


valid_base = "HTTPS://PAC.METTORIUS.COM/"


def from_url(url):
    return PAC_CAT.from_url(url, suppress_validation_errors=True)


def test_main_category_is_the_first_category():
    ''' `categories` re-parses on every access (no caching), and full model equality is
    unreliable here too (ValidationMessage.source_id=id(self) breaks == for any object
    that ever accumulated a validation message) - so compare by .key rather than by
    identity or full equality. '''
    pac = from_url(valid_base + "-DX/KEY:VAL/-MX/KEY:VAL")
    assert pac.main_category.key == pac.categories[0].key
    assert pac.main_category.key == '-DX'


def test_main_category_with_a_single_category():
    pac = from_url(valid_base + "-MD/240:BAL500/21:12345")
    assert pac.main_category.key == '-MD'
    assert pac.main_category.model_number == 'BAL500'


def test_processor_finds_the_processor_category_among_categories():
    pac = from_url(valid_base + "-DR/21:VAL/-PS/21:INSTANCE1/240:AURORA")
    assert isinstance(pac.processor, Processor_Software)
    assert pac.processor.processor_instance == 'INSTANCE1'
    assert pac.processor.processor_code == 'AURORA'


def test_processor_matches_the_misc_processor_category_too():
    pac = from_url(valid_base + "-DR/21:VAL/-PX/21:INSTANCE1")
    assert isinstance(pac.processor, Processor_Misc)
    
    
def test_processor_matches_the_instrument_processor_category_too():
    pac = from_url(valid_base + "-DR/21:VAL/-MD/240:MODEL/21:INSTANCE1")
    assert isinstance(pac.processor, Material_Device)
    
    
def test_instrument_as_main_category_has_no_processor():
    pac = from_url(valid_base + "-MD/240:MODEL/21:INSTANCE1")
    assert pac.processor is None


def test_processor_can_also_be_the_main_category():
    pac = from_url(valid_base + "-PS/21:INSTANCE1/240:AURORA")
    assert isinstance(pac.main_category, Processor_Software)

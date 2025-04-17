import pytest
from pydantic import ValidationError

from labfreed.pac_id import IDSegment
from labfreed.pac_cat import *

additional_segments=[IDSegment(key='K1', value='V1'),
                                         IDSegment(value='V2')]



def test_alias():
    md = Material_Device(serial_number='123', model_number='aa')
    md2 = Material_Device(**{'21': '123', '240': 'aa'})
    assert md == md2
    
def test_required_fields_MD():
    md = Material_Device(serial_number=None, model_number=None)
    assert not md.is_valid


md = Material_Device(model_number='BAL500', 
                    serial_number='1234', 
                    additional_segments=[IDSegment(key='K1', value='V1'),
                                         IDSegment(value='V2')])

        
def test_MD_segments():
    cat = md.to_identifier_category()
    assert cat.key == '-MD'
    assert cat.segments[0].key == '240'
    assert cat.segments[0].value == 'BAL500'
    assert cat.segments[1].key == '21'
    assert cat.segments[1].value == '1234'
    

    
    
def test_additional_segments():
    cat = md.to_identifier_category()
    assert cat.segments[2].key == 'K1'
    assert cat.segments[2].value == 'V1'
    assert cat.segments[3].key is None
    assert cat.segments[3].value == 'V2'
    
    
ms = Material_Substance(product_number='X67678',
                        batch_number='9999',
                        container_size='1000',
                        container_number='34',
                        aliquot='2',
                        additional_segments=additional_segments
                        )



def test_MS_segments():
    cat = ms.to_identifier_category()
    assert cat.key == '-MS'
    assert cat.segments[0].key == '240'
    assert cat.segments[0].value == 'X67678'
    assert cat.segments[1].key == '10'
    assert cat.segments[1].value == '9999'
    assert cat.segments[2].key == '20'
    assert cat.segments[2].value == '1000'
    assert cat.segments[3].key == '21'
    assert cat.segments[3].value == '34'
    assert cat.segments[4].key == '250'
    assert cat.segments[4].value == '2'
    
ms_some_empty = Material_Substance(product_number='X67678',
                        batch_number='9999',
                        aliquot='2',
                        additional_segments=additional_segments
                        )
    
def test_empty_segments_not_written():
    cat = PAC_CAT(categories=[md])
    assert cat.key == '-MS'
    assert cat.segments[0].key == '240'
    assert cat.segments[0].value == 'X67678'
    assert cat.segments[1].key == '10'
    assert cat.segments[1].value == '9999'
    assert cat.segments[2].key == '250'
    assert cat.segments[2].value == '2'


def test_short_notation():
    cat = ms.to_identifier_category(use_short_notation=True)
    assert cat.key == '-MS'
    assert cat.segments[0].key is None
    assert cat.segments[0].value == 'X67678'
    assert cat.segments[1].key is None
    assert cat.segments[1].value == '9999'
    assert cat.segments[2].key is None
    assert cat.segments[2].value == '1000'
    assert cat.segments[3].key is None
    assert cat.segments[3].value == '34'
    assert cat.segments[4].key is None
    assert cat.segments[4].value == '2'
    
def test_short_notation_break():
    cat = ms_some_empty.to_identifier_category(use_short_notation=True)
    assert cat.key == '-MS'
    assert cat.segments[0].key is None
    assert cat.segments[0].value == 'X67678'
    assert cat.segments[1].key is None
    assert cat.segments[1].value == '9999'
    assert cat.segments[2].key == '250'
    assert cat.segments[2].value == '2'
    
    
    

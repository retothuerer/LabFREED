import pytest
from pydantic import ValidationError

from labfreed.pac_cat.predefined_categories import Data_Static
from labfreed.pac_id import IDSegment
from labfreed.pac_cat import *

additional_segments=[IDSegment(key='K1', value='V1'),
                     IDSegment(value='V2')]



def test_alias():
    md = Material_Device(serial_number='123', model_number='aa')
    md2 = Material_Device(**{'21': '123', '240': 'aa'})
    assert md == md2
    
    
# Category MD
def test_required_fields_MD():
    md = Material_Device(serial_number=None, model_number=None)
    assert not md.is_valid

md = Material_Device(model_number='BAL500', 
                    serial_number='1234', 
                    additional_segments=additional_segments)
       
def test_MD_segments():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[md])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-MD/240:BAL500/21:1234/K1:V1/V2'


def test_MD_segments_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[md])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-MD/BAL500/1234/K1:V1/V2'
    

    

#Category MS
ms = Material_Substance(product_number='X67678',
                        batch_number='9999',
                        container_size='1000',
                        container_number='34',
                        aliquot='2',
                        additional_segments=additional_segments
                        )

def test_MS_segments():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[ms])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-MS/240:X67678/10:9999/20:1000/21:34/250:2/K1:V1/V2'
    
def test_MS_segments_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[ms])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-MS/X67678/9999/1000/34/2/K1:V1/V2'

    
ms_some_empty = Material_Substance(product_number='X67678',
                        batch_number='9999',
                        aliquot='2',
                        additional_segments=additional_segments
                        )

#Category MC
mc = Material_Consumable(product_number='X67678',
                        batch_number='9999',
                        packaging_size='1000',
                        serial_number='34',
                        aliquot='2',
                        additional_segments=additional_segments
                        )

def test_MC_segments():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[mc])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-MC/240:X67678/10:9999/20:1000/21:34/250:2/K1:V1/V2'
    
def test_MC_segments_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[mc])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-MC/X67678/9999/1000/34/2/K1:V1/V2'
    
    
    
#Category MM
mm = Material_Misc(product_number='X67678',
                        batch_number='9999',
                        packaging_size='1000',
                        serial_number='34',
                        aliquot='2',
                        additional_segments=additional_segments
                        )

def test_MM_segments():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[mm])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-MM/240:X67678/10:9999/20:1000/21:34/250:2/K1:V1/V2'
    
def test_MM_segments_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[mm])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-MM/X67678/9999/1000/34/2/K1:V1/V2'
    
    

#Category DR
dr = Data_Result(id='X67678',
                 additional_segments=additional_segments
                )

def test_DR_segments():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[dr])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-DR/21:X67678/K1:V1/V2'
    
def test_DR_segments_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[dr])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-DR/X67678/K1:V1/V2'
    
    
#Category DM
dm = Data_Method(id='X67678',
                 additional_segments=additional_segments
                )

def test_DM_segments():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[dm])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-DM/21:X67678/K1:V1/V2'
    
def test_DM_segments_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[dm])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-DM/X67678/K1:V1/V2'
    
    
#Category DP
dp = Data_Progress(id='X67678',
                 additional_segments=additional_segments
                )

def test_DP_segments():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[dp])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-DP/21:X67678/K1:V1/V2'
    
def test_DP_segments_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[dp])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-DP/X67678/K1:V1/V2'
    

#Category DC
dc = Data_Calibration(id='X67678',
                 additional_segments=additional_segments
                )

def test_DC_segments():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[dc])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-DC/21:X67678/K1:V1/V2'
    
def test_DC_segments_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[dc])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-DC/X67678/K1:V1/V2'
    
    
#Category DS
ds = Data_Static(id='X67678',
                 additional_segments=additional_segments
                )

def test_DS_segments():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[ds])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-DS/21:X67678/K1:V1/V2'
    
def test_DS_segments_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[ds])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-DS/X67678/K1:V1/V2'

    
    
    
ms_some_empty = Material_Substance(product_number='X67678',
                        batch_number='9999',
                        aliquot='2',
                        additional_segments=additional_segments
                        )
    
def test_empty_segments_not_written():
    
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[ms_some_empty])
    url = pac.to_url(use_short_notation=False)
    assert url == 'HTTPS://PAC.Q.COM/-MS/240:X67678/10:9999/250:2/K1:V1/V2'


def test_empty_segments_not_written_short_notation():
    pac = PAC_CAT.from_categories(issuer='Q.COM', categories=[ms_some_empty])
    url = pac.to_url(use_short_notation=True)
    assert url == 'HTTPS://PAC.Q.COM/-MS/X67678/9999/250:2/K1:V1/V2'
    

    
    
    

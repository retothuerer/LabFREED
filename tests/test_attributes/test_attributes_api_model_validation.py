from pydantic import ValidationError
import pytest
from labfreed.labfreed_infrastructure import LabFREED_ValidationError
from labfreed.pac_attributes.api_data_models.request import AttributeRequestPayload

dummy_pac = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/1234'

def test_number_pac_id_must_be_below_100():
    pac_urls = [dummy_pac for _ in range(0,100)]
    r = AttributeRequestPayload(pac_ids=pac_urls)
    assert r.is_valid
    
    pac_urls.append(dummy_pac)
    with pytest.raises((LabFREED_ValidationError, ValidationError)):
        AttributeRequestPayload(pac_ids=pac_urls)
    
def test_pac_url_must_be_valid():
    invalid_pac_url = 'HTTPS://PAC.METTORIUS.COM/-£MD/BAL500/1234'
    with pytest.raises((LabFREED_ValidationError, ValidationError)):
        AttributeRequestPayload(pac_ids=[invalid_pac_url])

    
def test_single_pac_url():
    r = AttributeRequestPayload(pac_ids=[dummy_pac])
    assert r.is_valid
    
import os
import pytest
from labfreed.pac_id_resolver import load_cit

# Get a CIT
@pytest.fixture
def cit():
    dir = os.path.dirname(__file__)
    p = os.path.join(dir, 'coupling-information-table')       
    cit = load_cit(p)
    return cit


def test_valid_cit(cit):
    assert cit.is_valid

def test_():
    ...
import pytest

from labfreed.well_known_keys.unece import ucum_bridge


@pytest.fixture
def without_ucum_support(monkeypatch):
    '''Forces ucum_bridge into its no-dependency fallback path for the duration of the test.

    monkeypatch reverts HAS_UCUM_SUPPORT to its original value on teardown, so this can never
    leak into other tests.
    '''
    monkeypatch.setattr(ucum_bridge, "HAS_UCUM_SUPPORT", False)

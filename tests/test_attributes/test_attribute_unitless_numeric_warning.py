'''
LabFREED has no unitless numbers (CLAUDE.md): Attribute._attribute_to_attribute_payload_type
already wraps a bare int/float value in Quantity(value=value, unit='dimensionless')
before serializing - it needs no code change, since the warning lives once, centrally,
in Quantity itself (see design-choices.md/CLAUDE.md). This just confirms that
centralization actually reaches this call site.
'''
import pytest

from labfreed.pac_attributes.facade.attributes import Attribute, Attributes


def test_bare_numeric_attribute_value_warns_on_payload_conversion():
    attributes = Attributes([Attribute(key="https://example.com/count", value=5)])
    with pytest.warns(UserWarning):
        attributes.to_payload_attributes()

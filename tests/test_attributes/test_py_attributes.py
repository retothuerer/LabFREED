import pytest

from labfreed.pac_attributes.client.client_attribute_group import ClientAttributeGroup
from labfreed.pac_attributes.facade.py_attributes import Attribute, AttributeGroup, Attributes


def test_from_attribute_group_round_trip_preserves_all_fields():
    # AttributeGroup.from_attribute_group has zero existing coverage; this locks in
    # its current, correct behavior across the vars() -> model_dump() refactor (see
    # design-choices.md).
    payload_attributes = Attributes([
        Attribute(key='https://example.com/foo', value='bar'),
    ]).to_payload_attributes()

    source = ClientAttributeGroup(
        group_key='group1',
        group_label='Group One',
        attributes=payload_attributes,
        origin='https://server.example.com',
        language='en',
    )

    result = AttributeGroup.from_attribute_group(source)

    assert result.group_key == 'group1'
    assert result.group_label == 'Group One'
    assert result.origin == 'https://server.example.com'
    assert result.language == 'en'
    assert 'https://example.com/foo' in result.attributes
    assert result.attributes['https://example.com/foo'].values == 'bar'

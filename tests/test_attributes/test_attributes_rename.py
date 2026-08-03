import pytest

from labfreed.pac_attributes.client.client_attribute_group import ClientAttributeGroup
from labfreed.pac_attributes.api_data_models.response import (
    Spec_Attribute,
    Spec_AttributeGroup,
    Attribute as OldAttribute,
    AttributeGroup as OldAttributeGroup,
)
from labfreed.pac_attributes.facade.attributes import (
    Attribute,
    AttributeGroup,
    Attributes,
    Reference,
    Resource,
    pyAttribute,
    pyAttributeGroup,
    pyAttributes,
    pyReference,
    pyResource,
)
from labfreed.pac_attributes.server.attribute_data_sources import (
    Spec_Dict_DataSource,
    Dict_DataSource as OldServerDict_DataSource,
)
from labfreed.pac_attributes.facade.dict_data_source import (
    Dict_DataSource,
    pyDict_DataSource,
)


# Covers the pac_attributes/facade rename: core Attribute/AttributeGroup -> Spec_Attribute/
# Spec_AttributeGroup (old names kept as deprecated aliases); wrapper pyAttribute/
# pyAttributeGroup/pyAttributes/pyReference/pyResource -> Attribute/AttributeGroup/
# Attributes/Reference/Resource (old py* names kept as deprecated aliases). See
# design-choices.md for the "flip the plain name onto the wrapper" reasoning.
#
# Dict_DataSource follows the same wrapper rename, but the plain name was already taken
# by the server-side class working with raw Spec_Attribute dicts - that class became
# Spec_Dict_DataSource (old name kept as a deprecated alias) to free up Dict_DataSource
# for the facade wrapper (formerly pyDict_DataSource, now also a deprecated alias).

def test_spec_attribute_is_the_renamed_core_type():
    attr = Spec_Attribute(key='k', label='l', items=[])
    assert isinstance(attr, Spec_Attribute)


def test_old_attribute_name_still_works_and_warns():
    with pytest.deprecated_call():
        attr = OldAttribute(key='k', label='l', items=[])
    assert isinstance(attr, OldAttribute)
    assert isinstance(attr, Spec_Attribute)


def test_old_attribute_group_name_still_works_and_warns():
    with pytest.deprecated_call():
        grp = OldAttributeGroup(group_key='g', attributes={})
    assert isinstance(grp, OldAttributeGroup)
    assert isinstance(grp, Spec_AttributeGroup)


def test_attribute_is_the_renamed_wrapper_type():
    attr = Attribute(key='https://example.com/foo', values='bar')
    assert isinstance(attr, Attribute)
    payload = Attributes([attr]).to_payload_attributes()
    assert isinstance(payload['https://example.com/foo'], Spec_Attribute)


def test_old_pyattribute_name_still_works_and_warns():
    with pytest.deprecated_call():
        attr = pyAttribute(key='https://example.com/foo', values='bar')
    assert isinstance(attr, pyAttribute)
    assert isinstance(attr, Attribute)


def test_old_pyattributes_name_still_works_and_warns():
    attr = Attribute(key='k', values='v')
    with pytest.deprecated_call():
        wrapped = pyAttributes([attr])
    assert isinstance(wrapped, pyAttributes)
    assert isinstance(wrapped, Attributes)


def test_attribute_group_from_attribute_group_respects_the_class_it_was_called_on():
    # from_attribute_group used to be a @staticmethod hardcoding pyAttributeGroup(**data);
    # it must become a @classmethod using cls(**data) so calling it via the deprecated
    # old class still returns an instance of that old class, not silently the new one.
    payload_attributes = Attributes([Attribute(key='k', values='v')]).to_payload_attributes()
    source = ClientAttributeGroup(
        group_key='g1', group_label='G', attributes=payload_attributes,
        origin='https://server.example.com', language='en',
    )

    new_result = AttributeGroup.from_attribute_group(source)
    assert isinstance(new_result, AttributeGroup)

    with pytest.deprecated_call():
        old_result = pyAttributeGroup.from_attribute_group(source)
    assert isinstance(old_result, pyAttributeGroup)


def test_old_pyreference_and_pyresource_still_work_and_warn():
    with pytest.deprecated_call():
        ref = pyReference('https://example.com/x')
    assert isinstance(ref, pyReference)
    assert isinstance(ref, Reference)

    with pytest.deprecated_call():
        res = pyResource('https://example.com/y')
    assert isinstance(res, pyResource)
    assert isinstance(res, Resource)


def test_spec_dict_data_source_is_the_renamed_core_type():
    ds = Spec_Dict_DataSource(attribute_group_key='g', data={})
    assert isinstance(ds, Spec_Dict_DataSource)


def test_old_server_dict_data_source_name_still_works_and_warns():
    with pytest.deprecated_call():
        ds = OldServerDict_DataSource(attribute_group_key='g', data={})
    assert isinstance(ds, OldServerDict_DataSource)
    assert isinstance(ds, Spec_Dict_DataSource)


def test_dict_data_source_is_the_renamed_facade_wrapper_type():
    ds = Dict_DataSource(attribute_group_key='g', data={'subj': Attributes([Attribute(key='k', values='v')])})
    assert isinstance(ds, Dict_DataSource)
    assert isinstance(ds, Spec_Dict_DataSource)
    group = ds.attributes('subj')
    assert isinstance(group, Spec_AttributeGroup)


def test_old_pydict_data_source_name_still_works_and_warns():
    with pytest.deprecated_call():
        ds = pyDict_DataSource(attribute_group_key='g', data={'subj': Attributes([Attribute(key='k', values='v')])})
    assert isinstance(ds, pyDict_DataSource)
    assert isinstance(ds, Dict_DataSource)

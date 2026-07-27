from labfreed.pac_id.extension import Extension


def test_name_without_type_is_invalid_but_does_not_raise():
    '''Constructing an Extension with a name but no type must be collected as a
    validation ERROR like every other constraint in this library, not raised as
    an exception -- that would break the graceful is_valid/errors() contract.'''
    ext = Extension(name='X', type=None, data='hello')
    assert not ext.is_valid
    assert len(ext.errors()) > 0


def test_type_without_name_is_invalid_but_does_not_raise():
    ext = Extension(name=None, type='X', data='hello')
    assert not ext.is_valid
    assert len(ext.errors()) > 0


def test_name_and_type_both_present_is_valid():
    ext = Extension(name='N', type='TEXT', data='hello')
    assert ext.is_valid


def test_name_and_type_both_absent_gives_recommendation_not_error():
    ext = Extension(name=None, type=None, data='hello')
    assert ext.is_valid
    assert len(ext.warnings()) > 0

'''
LabFREED has no unitless numbers (see CLAUDE.md, "LabFREED has no unitless
numbers"): Quantity(value, unit=None) is the one sanctioned way to represent a
genuinely dimensionless value, but it must always be an explicit, warned-about
choice, never a silent default. Quantity itself is the single place this is
enforced - every caller that ends up constructing a unitless Quantity (however
it got there: unit=None, unit='', unit='dimensionless') gets the same warning,
rather than each of T-REX/Attributes/etc. needing to remember to warn
separately.

Uses warnings.warn (not logging.warning) to match the existing precedent for
"silently assumed something" cases in this codebase (pac_attributes/facade/
attributes.py's missing-timezone-assumed-UTC warning), as opposed to
logging.warning's existing use for "unexpected input given" cases
(display_name_extension.py/text_base36_extension.py).
'''
import pytest

from labfreed.utilities.quantity import Quantity


def test_unit_none_warns():
    with pytest.warns(UserWarning):
        Quantity(value=5, unit=None)


def test_unit_dimensionless_string_warns():
    ''' 'dimensionless'/''/'1' are all normalized to unit=None internally
    (transform_inputs) - all three must warn, not just a bare None. '''
    for spelling in ["dimensionless", "", "1"]:
        with pytest.warns(UserWarning):
            Quantity(value=5, unit=spelling)


def test_real_unit_does_not_warn(recwarn):
    Quantity(value=5, unit="kg")
    assert len(recwarn) == 0

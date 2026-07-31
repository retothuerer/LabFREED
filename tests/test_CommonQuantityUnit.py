import pytest


def test_every_member_is_a_valid_ucum_unit():
    # imports deferred into the test body so collection doesn't error before
    # CommonQuantityUnit exists - only the (still-skipped) test run would.
    from labfreed.utilities.quantity import CommonQuantityUnit
    from labfreed.well_known_keys.unece import ucum_bridge

    for member in CommonQuantityUnit:
        assert ucum_bridge.is_valid_ucum(member.value), f"{member.name} = {member.value!r}"


def test_member_is_usable_directly_as_a_quantity_unit():
    # CommonQuantityUnit is a str subclass, so a member should work in place of a raw
    # UCUM string, without calling .value, wherever Quantity expects unit=...
    from labfreed.utilities.quantity import CommonQuantityUnit, Quantity

    q = Quantity(value=1, unit=CommonQuantityUnit.VOLUME_LITER)
    assert q.unit == "L"

"""consumer.py is just request/response DTOs (ActionResult and its three subclasses) -
these tests just pin down their defaults: a bare success needs nothing but `ok=True`,
and each subclass's extra field defaults to something falsy/None rather than being
required, since a failed action (ok=False) won't have a location_name/display_amount/
disposed flag to report.
"""
import pytest

from labfreed.labfreed_experimental.actions.consumer import (
    ActionResult,
    ContainerIsEmptyResult,
    UpdateAmountResult,
    UpdateLocationResult,
)


def test_bare_ok_result_needs_no_error():
    r = ActionResult(ok=True)
    assert r.error is None


def test_error_result_carries_a_message():
    r = ActionResult(ok=False, error="container not found")
    assert r.ok is False
    assert r.error == "container not found"


def test_update_location_result_defaults():
    r = UpdateLocationResult(ok=True)
    assert r.previous_location_pac_id is None
    assert r.location_name is None


def test_update_amount_result_defaults():
    r = UpdateAmountResult(ok=True)
    assert r.display_amount is None


def test_container_is_empty_result_defaults_to_not_disposed():
    r = ContainerIsEmptyResult(ok=True)
    assert r.disposed is False

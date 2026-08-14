import pytest

# GS1ApplicationIdentifier isn't imported anywhere in labfreed today (not even
# re-exported from well_known_keys/gs1/__init__.py) - this test exists on its own,
# independent of whether/when it gets wired into a consumer.
from labfreed.well_known_keys.gs1.gs1_ai_enum_sorted import GS1ApplicationIdentifier


def test_every_member_s_as_url_points_at_its_own_gs1_reference_page():
    for member in GS1ApplicationIdentifier:
        assert member.as_url() == f"ref.gs1.org/ai/{member.name}", member.name

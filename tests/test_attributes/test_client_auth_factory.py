import pytest
import requests

from labfreed.pac_attributes.api_data_models.request import AttributeRequestData
from labfreed.pac_attributes.client.auth import AuthRule, static_credential


class _CapturingAdapter(requests.adapters.HTTPAdapter):
    """Stands in for the network: records the outgoing request and returns a canned response."""

    def __init__(self):
        super().__init__()
        self.last_request: requests.PreparedRequest | None = None

    def send(self, request, **kwargs):
        self.last_request = request
        response = requests.Response()
        response.status_code = 200
        response._content = b"{}"
        return response


@pytest.fixture
def session_and_adapter():
    """A Session wired to a capturing adapter that stands in for the network."""
    adapter = _CapturingAdapter()
    session = requests.Session()
    session.mount("https://", adapter)
    return session, adapter


@pytest.fixture
def callback_factory():
    # Imported lazily: this factory doesn't exist yet (test-first), and importing it at
    # module level would turn every test in this file into a collection error instead of
    # a clean skip.
    from labfreed.pac_attributes.client.client import (
        authenticated_http_attribute_request_callback_factory,
    )

    return authenticated_http_attribute_request_callback_factory


@pytest.fixture
def rules():
    """The rules list handed to authenticated_http_attribute_request_callback_factory.

    Also the canonical example of wiring an AuthRule: match requests to
    api.example.com and inject the credential into X-Api-Key.
    """
    return [
        AuthRule(
            pattern="https://api.example.com/*",
            credential=static_credential("secret123"),
            header="X-Api-Key",
            scheme="",
        ),
    ]


def test_matching_rule_header_is_applied_to_the_actual_request(
    callback_factory, rules, session_and_adapter
):
    session, adapter = session_and_adapter
    callback = callback_factory(rules, session=session)
    request_data = AttributeRequestData(pac_id="HTTPS://PAC.EXAMPLE.COM/1")

    status_code, _ = callback("https://api.example.com/attributes", request_data)

    assert status_code == 200
    assert adapter.last_request.headers["X-Api-Key"] == "secret123"


def test_non_matching_rule_leaves_request_unauthenticated(
    callback_factory, rules, session_and_adapter
):
    session, adapter = session_and_adapter
    callback = callback_factory(rules, session=session)
    request_data = AttributeRequestData(pac_id="HTTPS://PAC.EXAMPLE.COM/1")

    callback("https://other.example.com/attributes", request_data)

    assert "X-Api-Key" not in adapter.last_request.headers


class _RaisingAdapter(requests.adapters.HTTPAdapter):
    """Stands in for a network failure: raises instead of returning a response."""

    def send(self, request, **kwargs):
        raise requests.exceptions.ConnectionError("boom")


def test_http_attribute_request_default_callback_factory_creates_its_own_session_when_none_given():
    from labfreed.pac_attributes.client.client import (
        http_attribute_request_default_callback_factory,
    )

    callback = http_attribute_request_default_callback_factory()
    assert callable(callback)


def test_authenticated_callback_factory_creates_its_own_session_when_none_given(
    rules, callback_factory
):
    callback = callback_factory(rules)
    assert callable(callback)


def test_default_callback_returns_500_when_the_request_raises():
    from labfreed.pac_attributes.client.client import (
        http_attribute_request_default_callback_factory,
    )

    session = requests.Session()
    session.mount("https://", _RaisingAdapter())
    callback = http_attribute_request_default_callback_factory(session=session)
    request_data = AttributeRequestData(pac_id="HTTPS://PAC.EXAMPLE.COM/1")

    status_code, body = callback("https://api.example.com/attributes", request_data)

    assert status_code == 500
    assert "boom" in body

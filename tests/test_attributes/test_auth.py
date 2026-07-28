import re

import pytest
import requests

from labfreed.pac_attributes.client.auth import (
    AuthRule,
    MissingEnvCredentialError,
    PatternMatchedAuth,
    env_credential,
    static_credential,
)


def _prepared_request(url: str) -> requests.PreparedRequest:
    return requests.Request(method="GET", url=url).prepare()


def test_matching_rule_sets_header():
    auth = PatternMatchedAuth([
        AuthRule(pattern="https://api.example.com/*",
                 credential=static_credential("secret123"),
                 header="X-Api-Key", scheme=""),
    ])
    request = auth(_prepared_request("https://api.example.com/attributes/HTTPS%3A%2F%2FPAC.EXAMPLE.COM%2F1"))
    assert request.headers["X-Api-Key"] == "secret123"


def test_non_matching_rule_leaves_request_unauthenticated():
    auth = PatternMatchedAuth([
        AuthRule(pattern="https://api.example.com/*",
                 credential=static_credential("secret123"),
                 header="X-Api-Key", scheme=""),
    ])
    request = auth(_prepared_request("https://other.example.com/attributes"))
    assert "X-Api-Key" not in request.headers


def test_default_scheme_is_bearer():
    auth = PatternMatchedAuth([
        AuthRule(pattern="https://api.example.com/*", credential=static_credential("tok")),
    ])
    request = auth(_prepared_request("https://api.example.com/attributes"))
    assert request.headers["Authorization"] == "Bearer tok"


def test_none_credential_skips_header():
    auth = PatternMatchedAuth([
        AuthRule(pattern="https://api.example.com/*", credential=static_credential(None)),
    ])
    request = auth(_prepared_request("https://api.example.com/attributes"))
    assert "Authorization" not in request.headers


def test_first_matching_rule_wins():
    auth = PatternMatchedAuth([
        AuthRule(pattern="https://api.example.com/*", credential=static_credential("first"), scheme=""),
        AuthRule(pattern="https://api.example.com/attributes*", credential=static_credential("second"), scheme=""),
    ])
    request = auth(_prepared_request("https://api.example.com/attributes"))
    assert request.headers["Authorization"] == "first"


def test_wildcards_on_both_sides_match_anywhere():
    auth = PatternMatchedAuth([
        AuthRule(pattern="*example.com*", credential=static_credential("tok"), scheme=""),
    ])
    request = auth(_prepared_request("https://sub.example.com/deep/path?query=1"))
    assert request.headers["Authorization"] == "tok"


def test_literal_dot_does_not_match_other_characters():
    auth = PatternMatchedAuth([
        AuthRule(pattern="*api.example.com*", credential=static_credential("tok"), scheme=""),
    ])
    request = auth(_prepared_request("https://apiXexampleXcom/attributes"))
    assert "Authorization" not in request.headers


def test_compiled_regex_pattern_is_used_as_regex():
    auth = PatternMatchedAuth([
        AuthRule(pattern=re.compile(r"api-\d+\.example\.com"),
                 credential=static_credential("tok"), scheme=""),
    ])
    request = auth(_prepared_request("https://api-42.example.com/attributes"))
    assert request.headers["Authorization"] == "tok"


def test_compiled_regex_pattern_non_match():
    auth = PatternMatchedAuth([
        AuthRule(pattern=re.compile(r"api-\d+\.example\.com"),
                 credential=static_credential("tok"), scheme=""),
    ])
    request = auth(_prepared_request("https://api-abc.example.com/attributes"))
    assert "Authorization" not in request.headers


def test_env_credential_reads_environment_variable(monkeypatch):
    monkeypatch.setenv("TEST_CREDENTIAL", "ABC")
    auth = PatternMatchedAuth([
        AuthRule(pattern="https://api.example.com/*",
                 credential=env_credential("TEST_CREDENTIAL"),
                 header="X-Api-Key", scheme=""),
    ])
    request = auth(_prepared_request("https://api.example.com/attributes"))
    assert request.headers["X-Api-Key"] == "ABC"


def test_env_credential_missing_variable_raises(monkeypatch):
    monkeypatch.delenv("TEST_CREDENTIAL", raising=False)
    auth = PatternMatchedAuth([
        AuthRule(pattern="https://api.example.com/*",
                 credential=env_credential("TEST_CREDENTIAL"),
                 header="X-Api-Key", scheme=""),
    ])
    with pytest.raises(MissingEnvCredentialError):
        auth(_prepared_request("https://api.example.com/attributes"))

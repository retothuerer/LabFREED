from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from typing import Callable

import requests

# Called fresh on every request rather than resolved once at startup, so the
# credential source (env var, DB, secret manager, ...) can change at runtime
# without restarting the process or invalidating any cache.
CredentialProvider = Callable[[], "str | None"]


class MissingEnvCredentialError(RuntimeError):
    """Raised when an env_credential's environment variable isn't set at request time.

    Declaring an AuthRule with env_credential is a promise that the variable will be
    set wherever the client runs. A missing variable means the deployment forgot to
    set it - not a legitimate "send this request unauthenticated" case - so this
    fails loudly instead of silently sending the request without the header.
    """


def env_credential(var_name: str) -> CredentialProvider:
    """CredentialProvider that reads an environment variable on every call.

    Raises MissingEnvCredentialError if the variable isn't set.
    """
    def read() -> str:
        try:
            return os.environ[var_name]
        except KeyError:
            raise MissingEnvCredentialError(
                f"Environment variable '{var_name}' is not set. "
                "This AuthRule requires it to be set at request time."
            ) from None
    return read


def static_credential(value: str | None) -> CredentialProvider:
    """CredentialProvider that always returns the same fixed value. Mostly useful for tests."""
    return lambda: value


@dataclass
class AuthRule:
    """One entry in a PatternMatchedAuth: which requests get which header injected.

    Args:
        pattern: either a glob checked against the outgoing request URL with
            fnmatch (`*` = any characters, `?` = one character, `[abc]` = one of
            a/b/c; put a `*` on either side to match anywhere, e.g.
            "*api-4lpexr44va-oa.a.run.app*" - literal characters like the dots
            in a hostname never need escaping), or a compiled regex
            (`re.compile(...)`, checked with `.search`) for the rare case a
            glob can't express what you need.
        credential: provider called per-request to get the secret value. If it
            returns None, the rule is treated as not applicable and no header is set.
        header: the HTTP header to set, e.g. "Authorization" or "X-Api-Key".
        scheme: prefix prepended to the credential value (e.g. "Bearer"). Use ""
            for headers that take the raw value, like most API-key headers.
    """
    pattern: str | re.Pattern
    credential: CredentialProvider
    header: str = "Authorization"
    scheme: str = "Bearer"

    def matches(self, url: str) -> bool:
        if isinstance(self.pattern, re.Pattern):
            return self.pattern.search(url) is not None
        return fnmatch.fnmatchcase(url, self.pattern)

    def render(self) -> str | None:
        value = self.credential()
        if value is None:
            return None
        return f"{self.scheme} {value}" if self.scheme else value


@dataclass
class PatternMatchedAuth(requests.auth.AuthBase):
    """A requests auth handler that injects credentials depending on which
    URL pattern the outgoing request matches. The first matching rule wins;
    requests matching no rule are sent unauthenticated.

    Attach to a Session so it applies to every request made through it:

        session = requests.Session()
        session.auth = PatternMatchedAuth([
            AuthRule(pattern="*api.example.com*",
                     credential=env_credential("EXAMPLE_API_KEY"),
                     header="X-Api-Key", scheme=""),
        ])
    """
    rules: list[AuthRule] = field(default_factory=list)

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        for rule in self.rules:
            if rule.matches(request.url):
                if value := rule.render():
                    request.headers[rule.header] = value
                break
        return request

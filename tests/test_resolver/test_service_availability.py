import pytest
import requests

from labfreed.pac_id_resolver import service_availability
from labfreed.pac_id_resolver.service_availability import check_service, check_service_group
from labfreed.pac_id_resolver.services import Service, ServiceGroup, ServiceStatus


def _service(**overrides):
    d = {
        'service_name': 'Service',
        'application_intents': ['view-apinilabs'],
        'service_type': 'userhandover-generic',
        'url': 'https://example.com',
    }
    d.update(overrides)
    return Service(**d)


class _StubResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class _StubSession:
    def __init__(self, status_code=None, raises=None):
        self._status_code = status_code
        self._raises = raises

    def head(self, url, timeout=None):
        if self._raises:
            raise self._raises
        return _StubResponse(self._status_code)


def test_check_service_marks_active_on_2xx_response():
    s = _service()
    check_service(s, session=_StubSession(status_code=200))
    assert s.status == ServiceStatus.ACTIVE


def test_check_service_marks_inactive_on_4xx_response():
    s = _service()
    check_service(s, session=_StubSession(status_code=404))
    assert s.status == ServiceStatus.INACTIVE


def test_check_service_marks_inactive_on_request_exception():
    s = _service()
    check_service(s, session=_StubSession(raises=requests.RequestException("boom")))
    assert s.status == ServiceStatus.INACTIVE


def test_check_service_group_checks_every_service(monkeypatch):
    monkeypatch.setattr(service_availability, '_has_internet_connection', lambda: True)
    group = ServiceGroup(origin='o', services=[
        _service(service_name='a'),
        _service(service_name='b'),
        _service(service_name='c'),
    ])
    check_service_group(group, session=_StubSession(status_code=200))
    assert all(s.status == ServiceStatus.ACTIVE for s in group.services)


def test_check_service_group_degrades_to_unknown_without_internet(monkeypatch):
    # a missed connectivity check must not raise and abort resolution -- it
    # should just mean "we don't know", not "this failed".
    monkeypatch.setattr(service_availability, '_has_internet_connection', lambda: False)
    group = ServiceGroup(origin='o', services=[_service(service_name='a'), _service(service_name='b')])
    check_service_group(group, session=_StubSession(status_code=200))
    assert all(s.status == ServiceStatus.UNKNOWN for s in group.services)

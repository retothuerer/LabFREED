import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from labfreed.pac_id_resolver.services import Service, ServiceGroup, ServiceStatus


__all__ = ["check_service", "check_service_group"]


def check_service(service: Service, session: requests.Session = None):
    '''Checks the availability of a single service, setting its .status.'''
    s = session or requests

    try:
        r = s.head(service.url, timeout=2)
        if r.status_code < 400:
            service.status = ServiceStatus.ACTIVE
        else:
            service.status = ServiceStatus.INACTIVE
    except requests.RequestException as e:
        logging.debug(f"Request failed: {e}")
        service.status = ServiceStatus.INACTIVE


def check_service_group(group: ServiceGroup, session: requests.Session = None):
    '''Triggers each service in the group to check if its url can be reached.
    Degrades every service to ServiceStatus.UNKNOWN instead of raising when
    there's no internet connection -- a missed connectivity check shouldn't
    invalidate an otherwise-successful resolution.'''
    if not _has_internet_connection():
        for s in group.services:
            s.status = ServiceStatus.UNKNOWN
        return
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_service, s, session=session) for s in group.services]
        for _ in as_completed(futures):
            pass  # just wait for all to finish


def _has_internet_connection():
    try:
        requests.get("https://1.1.1.1", timeout=3)
        return True
    except requests.RequestException:
        return False

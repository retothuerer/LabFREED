from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from urllib.parse import quote
import warnings

import requests

from pydantic import ValidationError

from labfreed.pac_attributes.api_data_models.request import AttributeRequestData
from labfreed.pac_attributes.api_data_models.response import Spec_AttributeGroup, AttributeResponsePayload
from labfreed.pac_attributes.client.auth import AuthRule, PatternMatchedAuth
from labfreed.pac_attributes.client.client_attribute_group import ClientAttributeGroup
from labfreed.pac_attributes.server.server import AttributeServerRequestHandler
from labfreed.pac_id.pac_id import PAC_ID


class AuthenticationError(Exception):
    '''Server rejected authentication. '''
    pass

class AttributeClientInternalError(Exception):
    '''The error is on client side. Possibly a bug on client side'''
    pass

class AttributeServerError(Exception):
    '''The error is on server side. Needs to contact the server admin'''
    pass



@runtime_checkable
class AttributeRequestCallback(Protocol):
    def __call__(self, url: str, attribute_request_data: AttributeRequestData) -> tuple[int, str]:
        '''handle the request
        returns a tuple of HTTP status code and the body of the response or an error message'''
        ...


def http_attribute_request_default_callback_factory(session: requests.Session = None) -> AttributeRequestCallback:
    """ Returns a default implementation of AttributeRequestCallback using `requests` package.

    Args:
        session (requests.Session, optional): A requests.Session object. Pass such an object if you need control over authentication and such things. If omitted a default Session is used.

    Returns:
        AttributeRequestCallback: a callback following the AttributeRequestCallback protocol.
    """
    if session is None:
        session = requests.Session()

    def callback(url: str, attribute_request_data: AttributeRequestData) -> tuple[int, str]:
        try:
            url = url + '/' + quote(attribute_request_data.subject_id, safe='')
            params = attribute_request_data.request_params()           
            resp = session.get(url, 
                               params = params,
                               headers=attribute_request_data.language_preference_http_header(),
                               timeout=10)
            return resp.status_code, resp.text
        except requests.exceptions.RequestException as e:
            return 500, str(e)
    return callback


def authenticated_http_attribute_request_callback_factory(
    rules: list[AuthRule], session: requests.Session = None
) -> AttributeRequestCallback:
    """ Returns a default implementation of AttributeRequestCallback using `requests` package,
    with per-request authentication headers injected based on which URL pattern the request matches.

    Args:
        rules: which requests get which credential/header, see PatternMatchedAuth and AuthRule.
        session (requests.Session, optional): A requests.Session object. If omitted a default Session is used.
            Its `auth` is set to a PatternMatchedAuth built from `rules`, overwriting any auth
            already set on it.

    Returns:
        AttributeRequestCallback: a callback following the AttributeRequestCallback protocol.
    """
    if session is None:
        session = requests.Session()
    session.auth = PatternMatchedAuth(rules)
    return http_attribute_request_default_callback_factory(session=session)


def local_attribute_request_callback_factory(request_handler:AttributeServerRequestHandler) -> AttributeRequestCallback:
    """ Returns a default implementation of AttributeRequestCallback using `requests` package.

    Args:
        request_handler: The request handler

    Returns:
        AttributeRequestCallback: a callback following the AttributeRequestCallback protocol.
    """

    def callback(url: str, attribute_request_data: AttributeRequestData) -> tuple[int, str]:
        try:
            resp = request_handler.handle_attribute_request(attribute_request_data)
            return 200, resp
        except requests.exceptions.RequestException as e:
            return 500, str(e)
    return callback

        
    

@dataclass
class AttributeClient():
    """ Client handling attribute requests over a caller-supplied HTTP callback.
    """
    http_post_callback:AttributeRequestCallback

    def get_attributes(self,
                       server_url:str,
                       subject_id:PAC_ID|str|None=None,
                       restrict_to_attribute_groups:list[str]|None=None,
                       language_preferences:list[str]|None=None,
                       **kwargs
                       ) -> list[Spec_AttributeGroup]:
        """Requests the attributes for one subject id from one attribute server. Always
        makes a fresh request via http_post_callback - there is no caching here.

        Args:
            server_url (str): the attribute server's base URL.
            subject_id (PAC_ID | str): the subject id to request attributes for. A PAC_ID
                instance is canonicalized via to_url(); a plain string is sent as-is.
            restrict_to_attribute_groups (list[str] | None, optional): if given, only
                request these attribute group keys. Defaults to None (all groups).
            language_preferences (list[str] | None, optional): preferred languages for
                translated attribute display names, most preferred first. Defaults to
                None (server default language).

        Raises:
            AuthenticationError:
            AttributeClientInternalError:
            AttributeServerError:

        Returns:
            list[ClientAttributeGroup]: attribute groups for the subject id
        """
        if 'pac_id' in kwargs:
            warnings.warn(
                "The 'pac_id' keyword argument to get_attributes() is deprecated, use 'subject_id' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            legacy_subject_id = kwargs.pop('pac_id')
            if subject_id is None:
                subject_id = legacy_subject_id
        if kwargs:
            raise TypeError(f"get_attributes() got unexpected keyword arguments: {sorted(kwargs)}")
        if subject_id is None:
            raise TypeError("get_attributes() missing required argument: 'subject_id'")

        # per PAC-ID-Attributes spec, subject_id only has to be an IRI - preferably, but not
        # necessarily, a PAC-ID. A PAC_ID instance is still canonicalized via to_url() (as
        # before); a plain string is sent through as-is. Routing an arbitrary IRI through
        # PAC_ID.from_url().to_url() would mangle it (e.g. injects a "PAC." issuer prefix),
        # so we deliberately don't parse/reserialize string input here.
        subject_id = subject_id.to_url() if isinstance(subject_id, PAC_ID) else subject_id

        # no valid data found in cache > request to server
        attribute_request_body = AttributeRequestData(subject_id=subject_id,
                                                        restrict_to_attribute_groups=restrict_to_attribute_groups,
                                                        language_preferences=language_preferences
                                )
        response_code, response_body_str = self.http_post_callback(server_url, attribute_request_body)

        if response_code == 400:
            raise AttributeClientInternalError(f"The server did not accept the request. Server message: '{response_body_str}'")
        if response_code == 401:
            raise AuthenticationError(f"Failed to authorize at the server. Server message: {response_body_str}")
        if response_code == 404:
            print(f'No atributes found for {subject_id}')
            return []
        if response_code == 500:
            raise AttributeServerError(f"The server accepted the request, but encountered an internal error. Contact the server admin. Server message: {response_body_str}")
        try:
            r = AttributeResponsePayload.model_validate_json(response_body_str)
        except ValidationError as e:
            print(e)
            raise AttributeServerError("The server accepted the request, and sent a reponse. However, the response is not adhering to the PAC Attributes specifications. Contact the server admin.")


        attribute_groups_out = []
        for ag_for_pac in r.data:
            if not ag_for_pac.attribute_groups:
                ags = []
            else:
                ags = [
                    ClientAttributeGroup(
                        group_key= ag.group_key,
                        attributes=ag.attributes,
                        origin=server_url,
                        language=r.language,
                        group_label=ag.group_label
                        )
                    for ag in ag_for_pac.attribute_groups
                    ]

            # compare the id from the response with the subject_id we requested attributes for
            # (the server echoes it back verbatim - see AttributeServerRequestHandler._get_attributes_for_pac_id).
            # if identical this is the part of the response we care about. other ids are just for the cache
            if subject_id == ag_for_pac.id:
                attribute_groups_out = ags

        return attribute_groups_out

            
                
    



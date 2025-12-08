from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from urllib.parse import quote

import requests

from pydantic import ValidationError
from werkzeug.datastructures import LanguageAccept 

from labfreed.pac_attributes.api_data_models.request import AttributeRequestData
from labfreed.pac_attributes.api_data_models.response import AttributeResponsePayload
from labfreed.pac_attributes.client.attribute_cache import AttributeCache, CacheableAttributeGroup
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
    def __call__(self, url: str, attribute_request_body: str) -> tuple[int, str]:
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
            url = url + '/' + quote(attribute_request_data.pac_id)
            params = {
                       "restrict_to_attribute_groups": attribute_request_data.restrict_to_attribute_groups, 
                      "suppress_forward_lookup": attribute_request_data.suppress_forward_lookup
                      } #session.get does url encode parameters automatically           
            resp = session.get(url, 
                               params = params,
                               headers=attribute_request_data.language_preference_http_header,
                               timeout=10)
            return resp.status_code, resp.text
        except requests.exceptions.RequestException as e:
            return 500, str(e)
    return callback


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
    """ Client handling attribute requests and caching thereof.
    """

    http_post_callback:AttributeRequestCallback
    cache_store:AttributeCache
    always_use_cached_value_for_minutes:int
                
    def get_attributes(self, 
                       server_url:str, 
                       pac_id:PAC_ID|str, 
                       restrict_to_attribute_groups:list[str]|None=None, 
                       language_preferences:list[str]|None=None,
                       force_server_request=False
                       ) -> list[CacheableAttributeGroup]:
        """gets the attributes from one attribute server for one PAC-ID. Uses a cached version if possible, otherwise requests from the server again.

        Args:
            server_url (str): _description_
            pac_id (PAC_ID | str): _description_
            restrict_to_attribute_groups (list[str] | None, optional): _description_. Defaults to None.
            language_preferences (list[str] | None, optional): _description_. Defaults to None.
            force_server_request (bool, optional): _description_. Defaults to False.

        Raises:
            AuthenticationError: 
            AttributeClientInternalError: 
            AttributeServerError: 

        Returns:
            list[CacheableAttributeGroup]: attribute groups for the PAC-ID
        """
        if isinstance(pac_id, str):
            pac_id = PAC_ID.from_url(pac_id)
        
        # try the cache
        if not force_server_request: 
            if restrict_to_attribute_groups:
                attribute_groups = self.cache_store.get_attribute_groups(server_url, pac_id, restrict_to_attribute_groups)
            else:
                attribute_groups = self.cache_store.get_all(server_url, pac_id)
                
            if attribute_groups and all([ag.still_valid(accept_cache_for_minutes=self.always_use_cached_value_for_minutes) for ag in attribute_groups]): 
                return attribute_groups
        
        # no valid data found in cache > request to server
        attribute_request_body = AttributeRequestData(pac_id=[pac_id.to_url()], 
                                                            restrict_to_attribute_groups=restrict_to_attribute_groups,
                                                            language_preferences=language_preferences
                                )
        response_code, response_body_str = self.http_post_callback(server_url, attribute_request_body.model_dump_json())

        if response_code == 400:
            raise AttributeClientInternalError(f"The server did not accept the request. Server message: '{response_body_str}'")
        if response_code == 401:
            raise AuthenticationError(f"Failed to authorize at the server. Server message: {response_body_str}")
        if response_code == 500:
            raise AttributeServerError(f"The server accepted the request, but encountered an internal error. Contact the server admin. Server message: {response_body_str}")
        try: 
            r = AttributeResponsePayload.model_validate_json(response_body_str)
        except ValidationError as e:
            print(e)
            raise AttributeServerError("The server accepted the request, and sent a reponse. However, the response is not adhering to the PAC Attributes specifications. Contact the server admin.")

        
        # update cache
        attribute_groups_out = []
        for ag_for_pac in r.pac_attributes:
            pac_from_response = PAC_ID.from_url(ag_for_pac.pac_id)
            ags = [
                CacheableAttributeGroup(
                    key= ag.key, 
                    attributes=ag.attributes, 
                    origin=server_url, 
                    language=r.language, 
                    label=ag.label,
                    value_from=datetime.now(tz=UTC)) 
                for ag in ag_for_pac.attribute_groups
                ]
            self.cache_store.update(server_url, pac_from_response, ags)
            
            # compare pac_id from response with pac_id we need attributes for.
            # if identical this is the part of the response we care about. other PAC-ID are just for the cache
            if pac_id.to_url() == pac_from_response.to_url():
                attribute_groups_out = ags
        
        return attribute_groups_out

            
                
    



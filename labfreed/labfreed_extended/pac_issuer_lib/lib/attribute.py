
import logging
from flask import render_template, request
from labfreed.pac_attributes.api_data_models.request import AttributeRequestData
from labfreed.pac_attributes.api_data_models.response import AttributeGroup
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_cat.predefined_categories import Material_Device, Material_Consumable, Material_Substance


from labfreed.pac_attributes.pythonic.py_attributes import pyAttributes, pyAttribute
from labfreed.pac_attributes.server.attribute_data_sources import AttributeGroupDataSource
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource

from labfreed.pac_attributes.server.server import AttributeServerRequestHandler


from labfreed.pac_attributes.pythonic.py_attributes import pyReference, pyResource
from labfreed.trex.pythonic import DataTable


from labfreed.utilities.translations import Terms, Term


from urllib.parse import urlparse

import requests
from requests import Response


import socket
from functools import lru_cache




def is_device(pac_url):
    pac_cat = PAC_CAT.from_url(pac_url)
    if not isinstance(pac_cat, PAC_CAT):
        return False
    is_device = isinstance(pac_cat.categories[0], Material_Device)
    return is_device

def model(pac_url):
    if not is_device(pac_url):
        return None
    cat:Material_Device = PAC_CAT.from_url(pac_url).categories[0]
    model = cat.model_number
    return model



class DynamicDemoAttributeGroup(AttributeGroupDataSource):
    
    def __init__(self, data, pac_filter_predicate=None, **kwargs):
        self._data = data
        self._pac_filter_predicate = pac_filter_predicate
        super().__init__(**kwargs)
     
    def is_static(self) -> bool:
        return False
    
    @property
    def provides_attributes(self):
        return [ d[0] for d in self._data ] 
    
    @property
    def translations(self) -> DictTranslationDataSource:
        return DictTranslationDataSource(
            supported_languages={'en'},
            data=Terms( terms=[ Term.create(d[0], d[2]) for d in self._data ])
        )

    
    def attributes(self, subject_id: str) -> AttributeGroup:
        if not self._pac_filter_predicate(subject_id):
            return None
        
        attributes = pyAttributes( [pyAttribute(key=d[0], value=d[1]) for d in self._data] ).to_payload_attributes()
        return AttributeGroup(group_key=self._attribute_group_key, 
                              attributes=attributes)
        
        
        
def product_number_from_pac_url(pac_url:str) -> str | None:
    """Safely extract model_number from PAC_CAT"""
    try:
        cat = PAC_CAT.from_url(pac_url)
        if not isinstance(cat, PAC_CAT):
            return None
        main_cat = PAC_CAT.from_url(pac_url).categories[0]
        if isinstance(main_cat, Material_Device):
            main_cat:Material_Device
            return main_cat.model_number
        if isinstance(main_cat, Material_Consumable):
            main_cat:Material_Consumable
            return main_cat.product_number
        if isinstance(main_cat, Material_Substance):
            main_cat:Material_Substance
            return main_cat.product_number
    except Exception:
        return None
    
    
class SessionLocalDirectCall(requests.Session):
    def __init__(self, request_handlers:dict[str, AttributeServerRequestHandler]):
        super().__init__() 
        self._request_handlers = request_handlers
        
    
    def get(self, url, *args, **kwargs):
    
        if is_self_request(url):
            # Case: server calls itself
            # handle differently, e.g., bypass HTTP, call function directly
            logging.warning(f'Handling call to {url} internally')
            parsed_url = urlparse(url)
            return self._handle_direct_call(parsed_url.path, *args, **kwargs)
        else:
            # normal POST via requests
            return super().post(url, *args, **kwargs)

    def _handle_direct_call(self, path:str, *args, **kwargs):
        # Example: directly call the Flask view function instead of HTTP
        # You could map URLs to functions if you know your routing
        # For now, just return a mock response
        path, pac = path.strip("/").rsplit("/", 1)
        rh = self._request_handlers.get(path)
        
        r = Response()
        if rh:
            request_data = AttributeRequestData.from_http_request(id = pac,
                                                                params = kwargs.get('params'),
                                                                 headers = kwargs.get('headers'))
            body = rh.handle_attribute_request(request_data=request_data)
            r.status_code = 200
            r._content = body.encode("utf-8")
            r.encoding = "utf-8"
            r.headers["Content-Type"] = "application/json; charset=utf-8"
        else:
            r.status_code = 404
            r._content = b"Invalid Request"

        return r
        


@lru_cache(maxsize=128)
def resolve_ip(host: str) -> str:
    """Resolve hostname to IP (with caching)."""
    return socket.gethostbyname(host)


def is_self_request(url: str) -> bool:
    parsed = urlparse(url)      
    
    target_host = parsed.hostname.lower()
    current_host = request.host.split(":")[0].lower()
    
    logging.warning(f'Request to target IP: {target_host}, current IP: {current_host}')

    # Shortcut for obvious loopback / link-local
    # Azur case (169.254.*.* → always self).
    if target_host in {"127.0.0.1", "localhost"} or target_host.startswith("169.254."):
        return True

    target_ip = resolve_ip(parsed.hostname.lower())
    current_ip = resolve_ip(request.host.split(":")[0].lower())
    
    return target_ip == current_ip


    
    
    
    
    
def render_template_with_results(pac_id, pac_info=None, cit="", hide_attribute_groups=[], pac_card_url_for=None, route_pac_id_url_for=None):
    return render_template('pac_info_main.jinja.html', 
                pac=pac_id, 
                pac_info = pac_info, 
                cit = cit,
                hide_attribute_groups=hide_attribute_groups, 
                is_data_table = lambda value: isinstance(value, DataTable),
                is_url = lambda s: isinstance(s, str) and urlparse(s).scheme in ('http', 'https') and bool(urlparse(s).netloc),
                is_image = lambda s: isinstance(s, pyResource) and s.root.lower().startswith('http') and s.root.lower().endswith(('.jpg','.jpeg','.png','.gif','.bmp','.webp','.svg','.tif','.tiff')),
                is_reference = lambda s: is_pac_id(s) or isinstance(s, pyReference),
                is_pac_id = is_pac_id,
                pac_card_url_for = pac_card_url_for,
                route_pac_id_url_for = route_pac_id_url_for
                )
    
def is_pac_id(v:str) -> bool:
    try:
        p = PAC_CAT.from_url(v)
        return True and 'PAC.' in v.upper()
    except Exception:
        return False


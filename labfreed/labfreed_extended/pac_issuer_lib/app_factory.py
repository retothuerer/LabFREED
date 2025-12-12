from dataclasses import dataclass
from functools import cache, partial, partialmethod
import logging
import os
from pathlib import Path
import re
import secrets
from typing import Any, Protocol
from uuid import uuid4
from jinja2 import ChoiceLoader, FileSystemLoader
import jinja2
from labfreed.labfreed_extended.pac_issuer_lib.lib.utils import add_ga_params, add_trace_id_params
from pydantic import BaseModel, Field

from flask import Blueprint, Flask, Response, current_app, flash, render_template, request, send_from_directory, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix


from labfreed.pac_cat.pac_cat import PAC_CAT

from labfreed.pac_attributes.pythonic.py_attributes import pyReference, pyResource
from labfreed.trex.pythonic import DataTable

from urllib.parse import urlparse

from labfreed import PAC_ID
from labfreed.labfreed_extended.app.app_infrastructure import Labfreed_App_Infrastructure
from labfreed.pac_attributes.pythonic.attribute_server_factory import AttributeFlaskApp
from labfreed.pac_attributes.server.server import AttributeServerRequestHandler

from labfreed.pac_attributes.server.attribute_data_sources import AttributeGroupDataSource
from labfreed.pac_attributes.server.translation_data_sources import TranslationDataSource, DictTranslationDataSource, Terms

from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo



from labfreed.labfreed_extended.pac_issuer_lib.lib.attribute import SessionLocalDirectCall

from werkzeug.middleware.proxy_fix import ProxyFix



class NavItem(BaseModel):
    href:str
    name:str
    icon_filename:str

class SiteMeta(BaseModel):
    site_title:str = "LabFREED Starter Kit Page"
    site_description:str = "LabFREED Starter Kit Page"
    site_author:str = "Unknown"
    nav_items:list[NavItem]|None = None
       
    

#TODO: find out why this doesnt work with BaseModel
@dataclass
class AttributeData():
    data_sources:list[AttributeGroupDataSource]
    default_language:str
    translation_data_sources:list[TranslationDataSource]
    
    
    
class PacInfoExtender(Protocol):
    ''' Protocol to inject an object, which analyzes a pac_info and extracts data for issuer specific use cases.'''
    @staticmethod
    def extend(pac_info: PacInfo) -> type[PacInfo]:
        ... 




class IssuerFlaskAppFactory():
    @classmethod
    def create_app( cls, 
                    issuer:str,
                    site_meta:SiteMeta|None = None, 
                    attribute_data:AttributeData|None = None, 
                    path_to_custom_resources:str|None = None,
                    app_secret:str|None = None,
                    pac_info_extender:PacInfoExtender|None = None,
                    resolver_macros:dict[str, str] = None,
                    use_issuer_resolver_config=True,
                    feature_flags:dict|None = None):
        
        app =  Flask(__name__, static_folder=None, static_url_path='/static') 
        
        if not feature_flags:
            feature_flags = dict()
        app.config['feature_flags'] = feature_flags
        
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

        
        if not app_secret:
            app.secret_key = str(secrets.token_hex())
        
        bp = cls.create_blueprint( issuer= issuer,
                                    as_multi_issuer_app=False,
                                    site_meta=site_meta,
                                    attribute_data=attribute_data,
                                    path_to_custom_resources=path_to_custom_resources,
                                    pac_info_extender=pac_info_extender,
                                    resolver_macros=resolver_macros,
                                    use_issuer_resolver_config = use_issuer_resolver_config)
        app.register_blueprint(bp)
        return app
    
    
    @classmethod
    def create_blueprint(   cls,
                            issuer:str,
                            as_multi_issuer_app:bool,
                            site_meta:SiteMeta|None = None, 
                            attribute_data:AttributeData|None = None, 
                            path_to_custom_resources:str|None = None,
                            pac_info_extender:PacInfoExtender|None = None,
                            resolver_macros:dict[str, str] = None, 
                            use_issuer_resolver_config=True):
        
        logging.info('initializing Blueprint')
        
        if not resolver_macros:
            resolver_macros = dict()
           
        issuer_name = issuer.split('.')[0]
       
        bp = Blueprint(issuer_name, __name__)
        
        if as_multi_issuer_app:
            bp.url_prefix = f"/{issuer_name}"
        
        # set up static fallback
        custom_static = Path(path_to_custom_resources) / "static"
        default_static = Path(__file__).parent / "static"

        # Override static route with fallback logic
        @bp.get("/static/<path:filename>")
        def static(filename):
            candidate = custom_static / filename
            if candidate.exists():
                return send_from_directory(custom_static, filename)
            return send_from_directory(default_static, filename)
        
        
        @cache
        def resolve_static_image(base_name: str) -> str | None:
            """
            Find the first matching image file for base_name with optional suffix
            (-something or _something) and allowed extensions.
            Checks custom static first, then default static.
            """
            
            base_name = Path(base_name).stem # This removes the last extension ("logo.svg" → "logo").

            exts = ["svg", "png", "jpg", "jpeg", "webp"]
            
            pattern = re.compile(rf"^{re.escape(base_name)}([-_]\w+)?\.({'|'.join(exts)})$")

            # check in custom first
            for folder in (custom_static, default_static):
                if not folder.exists():
                    continue
                for file in folder.iterdir():
                    if file.is_file() and pattern.match(file.name):
                        return url_for_within_issuer(f"static", filename=file.name)

            return None


        def url_for_within_issuer(endpoint, *args, **kwargs):
            if endpoint == "static":
                p = f'{issuer_name}.{endpoint}'
                url = url_for(p, *args, **kwargs)
                return url
            return url_for(endpoint, *args, **kwargs)
        
        
        @bp.context_processor
        def inject_helpers():
            return {"resolve_static_image": resolve_static_image,
                    "url_for_within_issuer": url_for_within_issuer,
                    'url_for': url_for_within_issuer
                    }
            
        def register_helpers(_bp):
            @_bp.context_processor
            def inject_helpers():
                return {"resolve_static_image": resolve_static_image,
                        "url_for_within_issuer": url_for_within_issuer,
                        'url_for': url_for_within_issuer
                        }
                
        register_helpers(bp)
            
        
        @bp.context_processor
        def inject_meta():
            d =   site_meta.model_dump() 
            return d
        
        
        '''
        Set up the attribute server
        =================
        We will create a server app with Flask. 
        '''
        if attribute_data:
            request_handler = AttributeServerRequestHandler(data_sources=attribute_data.data_sources, 
                                                            translation_data_sources= attribute_data.translation_data_sources, 
                                                            default_language=attribute_data.default_language
                                                            )


            bp_attribute_server = AttributeFlaskApp.create_attribute_blueprint(request_handler = request_handler)
            bp_attribute_server.url_prefix = '/attributes'
            register_helpers(bp_attribute_server)
            bp.register_blueprint(bp_attribute_server)



        '''
        Set up the PAC.issuer landing page
        =================
        We will create a server app with Flask. 
        '''
        bp_landing_page = Blueprint('landing_page', __name__ )
        
        
        # set up template loader
        issuer_templates = Path(path_to_custom_resources) / "templates"
        default_templates = Path(__file__).parent / "templates"
        if issuer_templates.exists():
            choice_loader = ChoiceLoader([
                        FileSystemLoader(str(issuer_templates)),
                        FileSystemLoader(str(default_templates))
                        ])
            choice_loader.issuer = issuer_name
            loader = choice_loader
        else:
            loader = FileSystemLoader(str(default_templates))
        bp.jinja_loader = loader
        bp_landing_page.jinja_loader = loader
        bp_attribute_server.jinja_loader = loader
            
            
        if attribute_data:
            if as_multi_issuer_app:
                request_handler_key = f'{issuer_name}/attributes'
            else:
                request_handler_key = 'attributes'
            http_client = SessionLocalDirectCall( request_handlers =
                {
                    request_handler_key: request_handler
                }
            )

            app_infrastructure = Labfreed_App_Infrastructure(language_preferences=attribute_data.default_language, 
                                                             http_client=http_client, 
                                                             use_issuer_resolver_config=use_issuer_resolver_config)
            bp._app_infrastructure = app_infrastructure
        
        
        # in order to have the resolver configuration work out of the box for services on this server 
        # the macro $HOST_URL$ can be used. Before the first request to this blueprint it needs to be initialized with the 
        # host address
        bp._resolver_configuration = None
        bp._resolver_macros = resolver_macros
        @bp.before_app_request
        def init_once():
             # Stays private to this module (since the name is prefixed with _.
            if not bp._resolver_configuration:
                # runs before the first request that hits *any* endpoint,
                # but we make sure it executes only once
                base_url = url_for(f'{issuer_name}.{bp_landing_page.name}.index', _external=True).rstrip('/')
                print("Init with base url", base_url)
                bp._base_url = base_url
                
                resolver_configuration_path = Path(path_to_custom_resources) / 'resolver_configuration.with_macros.yaml'
                if resolver_configuration_path.exists():
                    with open(resolver_configuration_path) as f:
                        rc = f.read()
                        
                    # Replace macros in resolver table
                    _resolver_configuration = rc
                    for macro, subst in bp._resolver_macros.items():
                        old = f'${{{macro}}}'
                        _resolver_configuration = _resolver_configuration.replace(old, subst )
                    _resolver_configuration = _resolver_configuration.replace("${BASE_URL}", base_url )
                    # Replace shorthand for array access by key
                    _resolver_configuration = re.sub(r'\[(".+?")\]', r'[?(@.key == \1)]', _resolver_configuration )
                    
                    logging.info(_resolver_configuration)
                    bp._resolver_configuration = _resolver_configuration
                    
                    app_infrastructure.add_resolver_config(_resolver_configuration)
                    
        # add the pac_info analyzer, too
        bp._pac_info_extender = pac_info_extender
        bp._site_meta = site_meta
        
        
        register_helpers(bp_landing_page)
            
                        
                
        @bp_landing_page.get('/')
        def index():
            return render_from_bp(bp, 'pac_issuer_error.jinja.html'), 404
        


        @bp_landing_page.get('/<path:path>')
        def pac_issuer_landingpage(path):
            if issuer:
                pac_id = f'HTTPS://PAC.{issuer}/{path}'.upper()
            else:
                pac_id = request.url
                pac_id, is_localhost = turn_local_host_to_valid_pac(pac_id, issuer)
            
            try: 
                pac_info = app_infrastructure.process_pac(pac_id)
            except Exception as e:
                logging.exception("Unhandled error")  # full traceback
                render_from_bp(bp, 'pac_issuer_error.jinja.html'), 404
            if not pac_info:
                render_from_bp(bp, 'pac_issuer_error.jinja.html'), 404
            
             
            # let the pac_info extender do it's job, if one was provided
            if a := bp._pac_info_extender:
                a:PacInfoExtender
                pac_info = a.extend(pac_info)
                
            hide_attribute_groups = [] 
            
            pac_card_url_for = partial(url_for,f'{issuer_name}.landing_page.pac_card')
            
            trace_id = uuid4() # used to trace calls to links ( espeially action links)
            session['trace_id']= trace_id
            
            return render_from_bp(
                        bp,
                        "pac_issuer_landing_page.jinja.html",
                        pac=pac_id, 
                        pac_info = pac_info, 
                        hide_attribute_groups=hide_attribute_groups,
                        pac_card_url_for = pac_card_url_for,
                        trace_id = trace_id
                        )
            


        def turn_local_host_to_valid_pac(pac_id, issuer=''):
            if is_localhost := "127.0.0.1" in pac_id:
                #remove localhost from string. including scheme and port, if existing
                pattern = re.compile(r'(?:https?:\/{0,2})?127\.0\.0\.1(?::\d+)?')
                s = re.sub(pattern, '', pac_id)
                if issuer:
                    cleaned_pac_id = f'HTTPS://PAC.{issuer.upper()}/{s}' 
                else:
                    cleaned_pac_id = f'HTTPS://PAC.{s}'
                cleaned_pac_id = cleaned_pac_id
                return cleaned_pac_id, is_localhost
            else:
                return pac_id, is_localhost

            
        @bp_landing_page.get('/resolver_config')
        @bp_landing_page.get('/resolver_config.yaml')
        def resolver_configuration():
            return Response(bp._resolver_configuration, mimetype="application/x-yaml")
        
        
        @bp_landing_page.get('/info_card')
        def pac_card():
            pac_id = request.args.get('pac_id')                
            try: 
                p = PAC_ID.from_url(pac_id)
                pac_valid = True
            except Exception as e:
                print(e)
                pac_valid = False
                
            pac_id, is_localhost = turn_local_host_to_valid_pac(pac_id)
            
            if not (pac_valid or is_localhost):
                issuer
                return ""
            
            pac_info = app_infrastructure.process_pac(pac_id)
            if a := bp._pac_info_extender:
                a:PacInfoExtender
                pac_info = a.extend(pac_info)
            response = render_from_bp(bp, 'pac_info/card.jinja.html', 
                                      pac_info=pac_info,
                                      **request.args
                                      )  
            return response
        
        # on local host for testing we need to circumvent the error, which is cause by PAC-ID validation when encountering the local host instead of issuer. 
        # TODO: make this cleaner and more stable
        bp.register_blueprint(bp_landing_page)
        
        @bp.get('/route_pac_id')
        def route_pac_id():
            pac_id = request.args.get('pac_id')
            raise NotImplementedError()
        
                
        def render_from_bp(bp, template_name, **context):
            # Make a new Jinja environment for this bp
            env = jinja2.Environment(loader=bp.jinja_loader)

            # Copy Flask globals/context
            env.globals.update(current_app.jinja_env.globals)
            
            trace_id = session.get('trace_id')
            d = {            
                "url_for_within_issuer": url_for_within_issuer,
                "resolve_static_image": resolve_static_image,
                "url_for": url_for_within_issuer,
                "with_ga_and_trace": lambda url: add_trace_id_params(add_ga_params(url, issuer), trace_id)
            }
            env.globals.update(d)
            
            env.globals.update({'site_meta': bp._site_meta.model_dump()})
            
            env.globals.update(render_context_utils)

            tpl = env.get_template(template_name)
            
            
            
            return tpl.render(**context)
        
        
        
        @bp.errorhandler(Exception)
        def not_found(error:Exception):
            logging.error(msg=error)
            return render_from_bp(bp, "pac_issuer_error.jinja.html", msg=str(error)), 404

        # @bp.errorhandler(500)
        # def internal_error(error):
        #     return render_from_bp("errors/pac_info_500.html"), 500
        
        
            
            
        return bp
    


def is_pac_id(v:str) -> bool:
    try:
        p = PAC_CAT.from_url(v)
        return True and 'PAC.' in v.upper()
    except Exception:
        return False
    
def title_format(s:str) -> str:
    """Convert snake_case string to NYTimes-style title."""
    return s.replace('_', ' ').title()
    
render_context_utils = {            
            "is_url": lambda s: isinstance(s, str) and urlparse(s).scheme in ('http', 'https') and bool(urlparse(s).netloc),
            "is_data_table": lambda value: isinstance(value, DataTable),
            "is_image": lambda s: isinstance(s, pyResource) and s.root.lower().startswith('http') and s.root.lower().endswith(('.jpg','.jpeg','.png','.gif','.bmp','.webp','.svg','.tif','.tiff')),
            "is_reference":lambda s: is_pac_id(s) or isinstance(s, pyReference),
            "is_pac_id": is_pac_id,
            "title_format": title_format,
            "zip": zip
        }
    
    
    
    
    
        

    
        





def attribute_data_from_module(module, default_language):
    try:
        ds = module.data_sources
    except AttributeError as e:
        raise AttributeError(f"Module {module!r} does not define 'data_sources'") from e
        
    try:
        tds = module.translation_data_sources
        if not tds:
            tds = [ DictTranslationDataSource(supported_languages={default_language}, data=Terms(terms=[]))]
    except AttributeError as e:
        tds = [ DictTranslationDataSource(supported_languages={default_language}, data=Terms(terms=[]))]
           
    attribute_data = AttributeData(default_language= default_language, 
                                   data_sources=ds,
                                   translation_data_sources=tds)
    
    return attribute_data


        


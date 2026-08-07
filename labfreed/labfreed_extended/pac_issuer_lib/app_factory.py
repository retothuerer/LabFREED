from functools import cache, partial, partialmethod, wraps
import ipaddress
import logging
import os
from pathlib import Path
import re
import secrets
import socket
from typing import Any, Callable, Protocol
from uuid import uuid4
from jinja2 import ChoiceLoader, FileSystemLoader
import jinja2
from labfreed.labfreed_extended.pac_issuer_lib.lib.utils import add_ga_params, add_trace_id_params
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from flask import Blueprint, Flask, Response, current_app, flash, make_response, render_template, request, send_from_directory, session, url_for, make_response
import flask_cors


from werkzeug.middleware.proxy_fix import ProxyFix


from urllib.parse import urlparse

from labfreed import PAC_ID
from labfreed.labfreed_extended.app.app_infrastructure import Labfreed_App_Infrastructure
from labfreed.labfreed_extended.pac_issuer_lib.lib.attribute_server_factory import AttributeFlaskApp
from labfreed.pac_attributes.server.server import AttributeServerRequestHandler

from labfreed.pac_attributes.server.attribute_data_sources import AttributeGroupDataSource
from labfreed.pac_attributes.server.translation_data_sources import TranslationDataSource, DictTranslationDataSource, Terms

from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo
from labfreed.labfreed_extended.pac_issuer_lib.lib.renderer_config import RendererConfig
from labfreed.labfreed_extended.pac_issuer_lib.lib.processor import default_processor_from_pac_extraction
from labfreed.pac_id_resolver.service_availability import check_service
from labfreed.pac_id_resolver.services import Service
from labfreed.labfreed_extended.pac_issuer_lib.lib.render_predicates import render_context_utils



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
    # Free text (the issuer can include a name/phone as extra lines if they want) -
    # rendered on the digital label as this issuer's own supplier contact address,
    # for the common case where the issuer is itself the product's supplier. This is
    # separate from a SUPPLIER attribute value being a PAC-ID reference to some other
    # entity (a distributor listing another manufacturer's product) - both can be
    # shown; neither is required.
    contact_address:str|None = None
       
    

class AttributeData(BaseModel):
    # AttributeGroupDataSource/TranslationDataSource are plain ABCs, not pydantic
    # types, so they need arbitrary_types_allowed - without it pydantic can't
    # generate a schema for them at all (that's what blocked this from being a
    # BaseModel like its sibling types).
    model_config = ConfigDict(arbitrary_types_allowed=True)

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
                    keep_duplicate_attributes:Literal["all", "first", "last"] = "all",
                    path_to_custom_resources:str|None = None,
                    app_secret:str|None = None,
                    pac_info_extender:PacInfoExtender|None = None,
                    resolver_macros:dict[str, str] = None,
                    use_issuer_resolver_config=False,
                    feature_flags:dict|None = None,
                    attribute_server_http_client=None,
                    renderer_config:RendererConfig|None = None,
                    processor_from_pac:Callable[[PacInfo], str|None] = default_processor_from_pac_extraction):
        
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
                                    keep_duplicate_attributes = keep_duplicate_attributes,
                                    path_to_custom_resources=path_to_custom_resources,
                                    pac_info_extender=pac_info_extender,
                                    resolver_macros=resolver_macros,
                                    use_issuer_resolver_config = use_issuer_resolver_config,
                                    attribute_server_http_client=attribute_server_http_client,
                                    renderer_config=renderer_config,
                                    processor_from_pac=processor_from_pac)
        app.register_blueprint(bp)
        
        # origins="*" + supports_credentials=True is a spec-invalid combination
        # (browsers reject credentialed wildcard-origin CORS outright). These
        # resources (attribute-server responses, resolver config YAML) are public,
        # read-only data meant to be fetched cross-origin by anyone - not something
        # that needs cookies/Authorization sent with the request - so drop
        # supports_credentials rather than scope origins down.
        flask_cors.CORS(app,
            origins="*",               # or a list of allowed origins
            methods=["GET"],           # list of allowed methods
            allow_headers=["Authorization", "Content-Type"],
            resources={
                r"/attributes/*": {},       # pattern-based CORS
                r"/resolver_config.*": {}
            })
        
        return app
    
    
    @classmethod
    def create_blueprint(   cls,
                            issuer:str,
                            as_multi_issuer_app:bool,
                            site_meta:SiteMeta|None = None,
                            attribute_data:AttributeData|None = None,
                            keep_duplicate_attributes:Literal["all", "first", "last"] = "all",
                            path_to_custom_resources:str|None = None,
                            pac_info_extender:PacInfoExtender|None = None,
                            resolver_macros:dict[str, str] = None,
                            use_issuer_resolver_config=False,
                            attribute_server_http_client=None,
                            renderer_config:RendererConfig|None = None,
                            processor_from_pac:Callable[[PacInfo], str|None] = default_processor_from_pac_extraction):
        
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
        
        
        '''
        Set up the attribute server
        =================
        We will create a server app with Flask. Optional: an issuer that only points to
        an external attribute service (via the resolver config) has no local data_sources
        and doesn't need this at all.
        '''
        bp_attribute_server = None
        if attribute_data:
            request_handler = AttributeServerRequestHandler(data_sources=attribute_data.data_sources,
                                                            translation_data_sources= attribute_data.translation_data_sources,
                                                            default_language=attribute_data.default_language,
                                                            keep_duplicate_attributes=keep_duplicate_attributes
                                                            )


            bp_attribute_server = AttributeFlaskApp.create_attribute_blueprint(request_handler = request_handler)
            bp_attribute_server.url_prefix = '/attributes'
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
        if bp_attribute_server:
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
        else:
            # no local attribute server - resolver-config-listed attribute-generic
            # services (e.g. an external server like Apini) are reached over a plain,
            # real HTTP client instead of the in-process SessionLocalDirectCall above.
            # attribute_server_http_client lets the caller supply one with auth
            # (e.g. PatternMatchedAuth) wired up for that external service.
            app_infrastructure = Labfreed_App_Infrastructure(http_client=attribute_server_http_client,
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
        bp._renderer_config = RendererConfig.labfreed_defaults().merge(renderer_config)
        bp._processor_from_pac = processor_from_pac

        @bp_landing_page.get('/')
        def index():
            return render_from_bp(bp, 'pac_issuer_error.jinja.html'), 404
        


        @bp_landing_page.get('/<path:path>')
        def pac_issuer_landingpage(path):
            base = request.blueprint.replace('.landing_page','')
            slow_content_url = base + '/slow_content/' + path
            timeout_url = base + '/timeout'

            return render_from_bp(bp,
                        "pac_issuer_landing_page_skeleton.jinja.html",
                        slow_content_url=slow_content_url,
                        timeout_url=timeout_url
                        )

        @bp_landing_page.get('/timeout')
        def pac_issuer_landing_page_timeout():
            return render_from_bp(bp, 'pac_issuer_error.jinja.html', msg="The request timed out. Please try again."), 408
            
        @bp_landing_page.get('/<path:anything>/slow_content/<path:path>')
        @bp_landing_page.get('/slow_content/<path:path>')
        def pac_issuer_landing_page_slow_content(path, anything=None):
            if issuer:
                pac_id = f'HTTPS://PAC.{issuer}/{path}'.upper()
            else:
                pac_id = request.url
                pac_id, is_localhost = turn_local_host_to_valid_pac(pac_id, issuer)
            
            try:
                pac_info = app_infrastructure.process_pac(pac_id)
            except Exception as e:
                logging.exception("Unhandled error")  # full traceback
                return render_from_bp(bp, 'pac_issuer_error.jinja.html'), 404
            if not pac_info:
                return render_from_bp(bp, 'pac_issuer_error.jinja.html'), 404
            
             
            # let the pac_info extender do it's job, if one was provided
            if a := bp._pac_info_extender:
                a:PacInfoExtender
                pac_info = a.extend(pac_info)

            # both resolved once, in Python, before rendering - see renderer_config.py /
            # processor.py. processor_pac_id is set first since a RendererRule predicate
            # could plausibly want to look at it.
            pac_info.processor_pac_id = bp._processor_from_pac(pac_info)
            content_template = bp._renderer_config.resolve_page_template(pac_info)

            hide_attribute_groups = []

            pac_card_url_for = partial(url_for,f'{issuer_name}.landing_page.pac_card')

            trace_id = uuid4() # used to trace calls to links ( espeially action links)
            session['trace_id']= trace_id

            return render_from_bp(
                        bp,
                        "pac_issuer_landing_page.jinja.html",
                        pac=pac_id,
                        pac_info = pac_info,
                        content_template = content_template,
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
                # Routine: pac_id is arbitrary query-param input, most of which
                # was never meant to be a valid PAC-ID at all.
                logging.debug(f"Invalid PAC-ID passed to /info_card: {e}")
                pac_valid = False

            pac_id, is_localhost = turn_local_host_to_valid_pac(pac_id)

            if not (pac_valid or is_localhost):
                return ""
            
            pac_info = app_infrastructure.process_pac(pac_id)
            if a := bp._pac_info_extender:
                a:PacInfoExtender
                pac_info = a.extend(pac_info)
            response = render_from_bp(bp, 'pac_info/card_standalone.jinja.html',
                                      pac_info=pac_info,
                                      **request.args
                                      )
            return response

        @bp_landing_page.get('/check_service')
        def check_service_route():
            # Runs the reachability check server-side (same-origin, no CORS blind spot)
            # but is only ever called async from the browser after the page has
            # already rendered, so it can't add latency to the initial response.
            url = request.args.get('url', '')
            if not _is_safe_service_url(url):
                return {'reachable': False}, 400
            s = Service(service_name='', application_intents=[], service_type='', url=url)
            check_service(s)
            return {'reachable': s.status.name == 'ACTIVE'}

        # on local host for testing we need to circumvent the error, which is cause by PAC-ID validation when encountering the local host instead of issuer. 
        # TODO: make this cleaner and more stable
        bp.register_blueprint(bp_landing_page)

        def _build_jinja_env(state):
            # Runs exactly once, when this blueprint is actually registered on an app
            # (via Blueprint.record_once) - that's the earliest point current_app/
            # state.app is available, and everything below is blueprint-constant
            # (fixed at create_blueprint() time), so building it once here - instead
            # of on every render_from_bp() call - avoids rebuilding the loader/globals/
            # template cache from scratch on every single request and card fetch.

            # create_app() sets this on app.config, but create_blueprint() is also
            # called directly (e.g. multi-issuer apps registering several blueprints on
            # one bare Flask app) without ever going through create_app() - so templates
            # relying on config.get('feature_flags') (e.g. the DEV debug banner in
            # pac_issuer_landing_page.jinja.html) would otherwise see a missing key.
            state.app.config.setdefault('feature_flags', {})

            env = jinja2.Environment(
                loader=bp.jinja_loader,
                autoescape=jinja2.select_autoescape(['html', 'htm', 'xml', 'xhtml']),
            )
            env.globals.update(state.app.jinja_env.globals)
            env.globals.update({
                "url_for_within_issuer": url_for_within_issuer,
                "resolve_static_image": resolve_static_image,
                "url_for": url_for_within_issuer,
                "check_service_url_for": lambda service_url: url_for(f'{issuer_name}.landing_page.check_service_route', url=service_url),
                "site_meta": bp._site_meta.model_dump(),
            })
            env.globals.update(render_context_utils)
            bp._jinja_env = env

        bp.record_once(_build_jinja_env)

        def render_from_bp(bp, template_name, **context):
            # trace_id is read fresh from the session on every call - genuinely
            # per-request, unlike everything baked into bp._jinja_env above - so it's
            # passed through render() instead of being a persistent env global.
            trace_id = session.get('trace_id')
            tpl = bp._jinja_env.get_template(template_name)
            return tpl.render(
                with_ga_and_trace=lambda url: add_trace_id_params(add_ga_params(url, issuer), trace_id),
                **context,
            )
        
        
        
        @bp.errorhandler(Exception)
        def not_found(error:Exception):
            if current_app.debug:
                raise  # ← critical: hand control back to Werkzeug
            
            logging.error(msg=error)
            return render_from_bp(bp, "pac_issuer_error.jinja.html", msg=str(error)), 404

        # @bp.errorhandler(500)
        # def internal_error(error):
        #     return render_from_bp("errors/pac_info_500.html"), 500
        
        
            
            
        return bp
    


def _is_safe_service_url(url: str) -> bool:
    """Reject loopback/private/link-local/reserved targets before the server issues a
    HEAD request to them - /check_service takes an arbitrary URL from a query param,
    so without this it's an SSRF oracle (probing internal hosts/ports via the reachable
    status it returns)."""
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return False
    try:
        addrinfos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        return False
    for info in addrinfos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True
    
    
    
    
    
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



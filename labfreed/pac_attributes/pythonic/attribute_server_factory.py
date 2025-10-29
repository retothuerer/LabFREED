from enum import Enum
from typing import Any, Protocol

from flask import Blueprint, current_app, url_for
from labfreed.pac_attributes.api_data_models.request import AttributeRequestPayload
from labfreed.pac_attributes.server.server import AttributeGroupDataSource, AttributeServerRequestHandler, InvalidRequestError, TranslationDataSource

try:
    from flask import Flask, Response, request
except ImportError:
    raise ImportError("Please install labfreed with the [extended] extra: pip install labfreed[extended]")



class Authenticator(Protocol):
    def __call__(self, request) -> bool: ...
    
class NoAuthRequiredAuthenticator(Authenticator):
    def __call__(self, request) -> bool:
        return True

class Webframework(Enum):
    FLASK = "flask"
    FASTAPI = 'fastapi'
    

class AttributeServerFactory():
    @staticmethod
    def create_server_app( datasources:list[AttributeGroupDataSource], 
                           default_language:str,
                           translation_data_sources:list[TranslationDataSource],
                           authenticator: Authenticator|None,
                           framework:Webframework=Webframework.FLASK,
                           doc_text:str=""
                           ):
        
        if not authenticator:
            raise ValueError("authenticator missing. Either define your own authenticator by implementing the 'Authenticator' Protocol, or - if you do not need authentication - explicitly pass a 'NoAuthRequiredAuthenticator' object")
            
        request_handler = AttributeServerRequestHandler(data_sources=datasources, 
                                                        translation_data_sources= translation_data_sources, 
                                                        default_language=default_language
                                                        )
            
        match(framework):
            case Webframework.FLASK:
                app = AttributeFlaskApp(request_handler,authenticator=authenticator, doc_text=doc_text)
                return app
            case Webframework.FASTAPI:
                raise NotImplementedError('FastAPI webapp not implemented')

            


            
class AttributeFlaskApp(Flask):
    def __init__(self, request_handler: AttributeServerRequestHandler, authenticator: Authenticator | None = None, doc_text:str="", **kwargs: Any):
        super().__init__(__name__, **kwargs)
        self.config['ATTRIBUTE_REQUEST_HANDLER'] = request_handler
        self.config['AUTHENTICATOR'] = authenticator
        self.config['DOC_TEXT'] = doc_text
        
        bp = self.create_attribute_blueprint(request_handler, authenticator)
        self.register_blueprint(bp)

    @staticmethod
    def create_attribute_blueprint(
        request_handler: AttributeServerRequestHandler,
        authenticator: Authenticator | None = None,
    ) -> Blueprint:
        bp = Blueprint("attribute", __name__)

        @bp.route("/", methods=["POST"], strict_slashes=False)
        def handle_attribute_request():
            if authenticator and not authenticator(request):
                return Response(
                    "Unauthorized", 401,
                    {"WWW-Authenticate": 'Basic realm="Login required"'}
                )
            try:
                json_request_body = request.get_data(as_text=True)
                response_body = request_handler.handle_attribute_request(json_request_body)
            except InvalidRequestError as e:
                print(e)
                return "Invalid request", 400
            except Exception as e:
                print(e)
                return "The request was valid, but the server encountered an error", 500
            return (response_body, 200, {"Content-Type": "application/json; charset=utf-8"})

        @bp.route("/", methods=["GET"], strict_slashes=False)
        def capabilities():
            doc_text = current_app.config.get('DOC_TEXT', "") 
            capabilities = request_handler.capabilities()
            authentication_required = bool(current_app.config.get('AUTHENTICATOR'))
            example_request = AttributeRequestPayload(pac_ids=['HTTPS://PAC.METTORIUS.COM/EXAMPLE'], language_preferences=['fr', 'de']).model_dump_json(indent=2, exclude_none=True, exclude_unset=True)
            server_address = request.url.rstrip('/')
            css_url = url_for("static", filename="style.css")
            response = f'''
                <html>
                    <head>
                        <link rel="stylesheet" type="text/css" href="{css_url}">
                    </head>

                    <body>
                        This is a <h1>LabFREED attribute server </h1>
                        <h2>Capabilities</h2>
                        Available Attribute Groups <br> {''.join([f'<a href="{ag}"> {ag} </a><br>' for ag in capabilities.available_attribute_groups])} <br>
                        
                        Supported Languages: {', '.join([f'<b> {l} </b>' for l in capabilities.supported_languages])} <br><br>
                        Default Language: <b>{capabilities.default_language}</b> <br>
                        

                        <h2>How to use</h2>
                        Make a <b>POST</b> request to <a href="{server_address}">{server_address}</a> with the following body:
                        <pre>{example_request}</pre>
                        Consult <a href="https://github.com/ApiniLabs/PAC-Attributes"> the specification </a> for details. <br>

                        
                        {'This server <b> requires authentication </b> ' if authentication_required else ''}  
                        <br>
                        
                        {"<h2>Further Information</h2>"if doc_text else ""} 
                        {doc_text or ""} 
                        

                    </body>
                </html>
    '''
        
            return response

        return bp
    
    



    

    
    
    

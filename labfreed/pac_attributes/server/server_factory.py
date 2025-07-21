from enum import Enum
from typing import Any
from flask import Flask, current_app, request
from labfreed.pac_attributes.api_data_models.request import AttributeRequestPayload
from labfreed.pac_attributes.server.server import AttributeGroupDataSource, AttributeServerRequestHandler, InvalidRequestError, TranslationDataSource

# from fastapi import FastAPI, Request



class Webframework(Enum):
    FLASK = "flask"
    FASTAPI = 'fastapi'

class AttributeServerFactory():
    @staticmethod
    def create_server_app( datasources:list[AttributeGroupDataSource], 
                           translation_data_source:TranslationDataSource|None = None,
                           framework:Webframework=Webframework.FLASK
                           ):
            
        request_handler = AttributeServerRequestHandler(data_sources=datasources, translation_data_source=translation_data_source)
            
        match(framework):
            case Webframework.FLASK:
                app = AttributeFlaskApp(__name__, request_handler)
                return app
            case Webframework.FASTAPI:
                raise NotImplementedError('FastAPI webapp not implemented')

            

            
            
            
class AttributeFlaskApp(Flask):
    def __init__(self, import_name: str, request_handler: AttributeServerRequestHandler, **kwargs: Any):
        super().__init__(import_name, **kwargs)
        self.config['ATTRIBUTE_REQUEST_HANDLER'] = request_handler
        self.add_url_rule('/', view_func=self.handle_attribute_request, methods=['GET'])

    def handle_attribute_request(self):
        try:
            json_request_body = request.get_data(as_text=True)
            handler: AttributeServerRequestHandler = self.config['ATTRIBUTE_REQUEST_HANDLER']
            response_body = handler.handle_attribute_request(json_request_body)
        except InvalidRequestError as e:
            print(e)
            return 'Invalid request', 400
        except Exception as e:
            return 'The request was valid, but the server encountered an error', 500
        return response_body
    
    
    
            #     app = FastAPI()

            #     # Inject your handler during startup
            #     app.state.request_handler = request_handler

            #     # --- Route handler ---
            #     @app.get("/")
            #     async def handle_attribute_request(request: Request):
            #         try:
            #             json_request_body = await request.json()
            #         except Exception:
            #             payload = AttributeRequestPayload(
            #                 pac_urls_without_extensions=["HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340"]
            #             )
            #             json_request_body = payload.as_json()

            #         request_handler: AttributeServerRequestHandler = request.app.state.request_handler
            #         response_body = request_handler.handle_attribute_request(json_request_body)
            #         return response_body
                
            #     return app
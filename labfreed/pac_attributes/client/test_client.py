
import requests

from labfreed.pac_attributes.client.client import AttributeClient


http_client = requests.Session(headers={"Authorization": "Bearer secret"})
def demo_callback(url:str, attribute_request_body=str, params:dict=None):
    return http_client.get(url=url, json=attribute_request_body, params=params)
attribute_client = AttributeClient()

pac = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340"
server_url = '127.0.0.1'
attribute_client.get_attributes(server_url, pac)



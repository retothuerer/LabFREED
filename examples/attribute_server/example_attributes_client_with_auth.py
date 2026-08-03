'''
This example shows a client authenticating itself when requesting attributes from a
protected attribute server, using AuthRule and authenticated_http_attribute_request_callback_factory.

It starts a minimal attribute server (protected with Basic auth) in a background thread, then
queries it like a real deployment would: a real requests.Session making a real HTTP request, with
a real Authorization header attached.
'''
import base64
import threading
import time

from flask import Request

from labfreed.pac_attributes.api_data_models.response import Spec_Attribute, TextAttributeItemsElement
from labfreed.labfreed_extended.pac_issuer_lib.lib.attribute_server_factory import AttributeServerFactory, Webframework
from labfreed.pac_attributes.server.attribute_data_sources import Dict_DataSource
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource
from labfreed.pac_attributes.well_known_attribute_keys import MetaAttributeKeys
from labfreed.utilities.translations import Terms, Term

from labfreed.pac_attributes.client.auth import AuthRule, static_credential
from labfreed.pac_attributes.client.client import AttributeClient, authenticated_http_attribute_request_callback_factory

PAC_STR = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001'

data_source = Dict_DataSource(
    attribute_group_key=MetaAttributeKeys.GROUPKEY,
    data={
        PAC_STR: {
            MetaAttributeKeys.DISPLAYNAME: Spec_Attribute(
                key=MetaAttributeKeys.DISPLAYNAME,
                label='Display Name',
                items=[TextAttributeItemsElement(value='My Balance')],
            ),
        }
    },
)
translations = DictTranslationDataSource(
    supported_languages={'en'},
    data=Terms(terms=[
        Term.create(MetaAttributeKeys.GROUPKEY, [('en', 'Meta Data')]),
        Term.create(MetaAttributeKeys.DISPLAYNAME, [('en', 'Display Name')]),
    ]),
)


# It is the server's responsibility to check credentials - the labfreed library only calls
# whatever Authenticator you give it. This one accepts Basic auth for user "test", password "1234".
class DemoAuthenticator:
    def __call__(self, request: Request) -> bool:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            return False
        try:
            user, pw = base64.b64decode(auth_header.split(' ', 1)[1]).decode().split(':', 1)
        except Exception:
            return False
        return user == 'test' and pw == '1234'


PORT = 5001
SERVER_URL = f'http://127.0.0.1:{PORT}'

app = AttributeServerFactory.create_server_app(
    framework=Webframework.FLASK,
    datasources=[data_source],
    default_language='en',
    translation_data_sources=[translations],
    authenticator=DemoAuthenticator(),
)
server_thread = threading.Thread(target=lambda: app.run(port=PORT, use_reloader=False), daemon=True)
server_thread.start()
time.sleep(1)  # give Flask a moment to start listening


# AuthRule.render() only prepends `scheme` to the credential value - it doesn't base64 encode it
# for you - so that encoding has to happen before it's handed to static_credential.
basic_auth_value = base64.b64encode(b'test:1234').decode()

rules = [
    AuthRule(pattern=f'{SERVER_URL}/*',
             credential=static_credential(basic_auth_value),
             header='Authorization', scheme='Basic'),
]

client = AttributeClient(
    http_post_callback=authenticated_http_attribute_request_callback_factory(rules)
)

attribute_groups = client.get_attributes(server_url=SERVER_URL, pac_id=PAC_STR)
for group in attribute_groups:
    for attr in group.attributes.values():
        values = ', '.join(str(item.value) for item in attr.items)
        print(f'{attr.label}: {values}')

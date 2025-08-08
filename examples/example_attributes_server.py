import base64
from datetime import datetime, timezone
import os
import random

from flask import Request
from labfreed.pac_attributes.pythonic.py_attributes import pyAttribute, pyAttributes, pyReference
from labfreed.pac_attributes.pythonic.py_dict_data_source import pyDict_DataSource
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_cat.predefined_categories import Material_Device
from labfreed.utilities.translations import Terms, Term
from labfreed.pac_attributes.api_data_models.response import AttributeGroup
from labfreed.pac_attributes.well_knonw_attribute_keys import MetaAttributeKeys

from labfreed.pac_attributes.server.attribute_data_sources import AttributeGroupDataSource
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource

from labfreed.trex.pythonic.quantity import Quantity

from labfreed.pac_attributes.pythonic.attribute_server_factory import AttributeServerFactory, Webframework
from labfreed.pac_attributes.pythonic.excel_attribute_data_source import LocalExcelAttributeDataSource
data_sources = []
transation_data_sources = []

'''
This example shows you how to setup an attribute server. 

We will create three attribute datasources, each becoming the source for one attribute group.
We will add translations in English and French 

Finally we will use flask and run the server locally.
'''


''' 
Attribute Group Example 1
=========
Create a datasource. For this demo let's use a Dict_DataSource, and configure it here in code.
NOTE: Such a metadata source is good practice to include
'''
data_sources.append(
    pyDict_DataSource( 
        attribute_group_key=MetaAttributeKeys.GROUPKEY.value,
        include_extensions=False,
        data = {
            # first entry of a balance
            "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001": pyAttributes([
                pyAttribute(key=MetaAttributeKeys.DISPLAYNAME.value, value="My Balance"),
                pyAttribute(key=MetaAttributeKeys.IMAGE, value="https://picsum.photos/id/82/200"),
            ]),
            
            # this is for a calibration weight, which is referenced by attributes of the balances
            "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002": pyAttributes([
                pyAttribute(key=MetaAttributeKeys.DISPLAYNAME.value, value="Calibration Weight PRN003"),
                pyAttribute(key=MetaAttributeKeys.IMAGE, value="https://picsum.photos/id/86/200"),
            ])
        } 
    )
)   

# we need to provide translations. Set this up for English and French
transation_data_sources.append(
    DictTranslationDataSource(
        supported_languages={'en', 'fr'},
        data=Terms(
                terms=[
                    Term.create(MetaAttributeKeys.GROUPKEY, [('en', 'MetaData'), ('fr', 'Métadonnées')]),
                    Term.create(MetaAttributeKeys.DISPLAYNAME.value, [('en', 'Display Name'), ('fr', 'Nom visuel')]),
                    Term.create(MetaAttributeKeys.IMAGE.value, [('en', 'Image'), ('fr', 'Image')]),
                ]
            )
    )
)



''' 
Attribute Group Example 2
=========
Use an Excel file as data source.
'''
fp = os.path.join(os.path.dirname(__file__), 'excel_attribute_data.xlsx')
data_sources.append(
    LocalExcelAttributeDataSource(
        attribute_group_key="https://mettorius.com/terms/attribute_group_excel", 
        file_path=fp, 
        include_extensions=False, base_url="https://labfreed.org/terms/example/")
)

transation_data_sources.append(
    DictTranslationDataSource(
        supported_languages={'en', 'fr'},
        data=Terms(
            terms=[
                Term.create("https://mettorius.com/terms/attribute_group_excel", [('en', "Calibration"), ('fr', 'Calibration')]),
                Term.create("https://labfreed.org/terms/example/Location", [('en', "Location"), ('fr', 'Emplacement')]),
                Term.create("https://labfreed.org/terms/example/LastCalibration", [('en', "Last Calibration"), ('fr', 'Dernier étalonnage')]),
                Term.create("https://labfreed.org/terms/example/isOK", [('en', "Is OK"), ('fr', 'Fonctionne')]),
                Term.create("https://labfreed.org/terms/example/NominalWeight", [('en', "Nominal Weight"), ('fr', 'Poids nominal"')]),
                Term.create("https://labfreed.org/terms/example/CalibratedWeight", [('en', "Calibrated Weight"), ('fr', 'Poids étalonné')]),
            ]
        )
    )
)



''' 
Attribute Group Example 3
=========
This time we create our own attribute data source. Let's make it so that it returns random values of each attribute type, 
but only for BAL500 balances
'''
class DynamicDemoAttributeGroup(AttributeGroupDataSource):
        
    def is_static(self) -> bool:
        return False
    
    @property
    def provides_attributes(self):
        return [
            "https://labfreed.org/terms/example/TextAttribute",
            "https://labfreed.org/terms/example/NumericAttribute",
            "https://labfreed.org/terms/example/ReferenceAttribute",
            "https://labfreed.org/terms/example/DateTimeAttribute",
            "https://labfreed.org/terms/example/BoolAttribute",
            "https://labfreed.org/terms/example/ObjectAttribute"
        ]
    
    def attributes(self, pac_url: str) -> AttributeGroup:
        # Check if we deal with a BAL500. We can make use of the full might of PAC-CAT
        pac_cat = PAC_CAT.from_url(pac_url)
        cat: Material_Device = pac_cat.get_category("-MD")
        if not cat.model_number == "BAL500":
            return None
        
        attributes = pyAttributes(
                [
                    pyAttribute(key="https://labfreed.org/terms/example/TextAttribute", value=random.choice(["Foo", "Bar"])),
                    pyAttribute(key="https://labfreed.org/terms/example/NumericAttribute", value=Quantity(value=round(random.uniform(0, 100), 2), unit=random.choice(["m", "kg", "mol/L"]))),
                    pyAttribute(key="https://labfreed.org/terms/example/ReferenceAttribute", value=pyReference('HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002')),
                    pyAttribute(key="https://labfreed.org/terms/example/DateTimeAttribute", value=datetime.now(tz=timezone.utc)),
                    pyAttribute(key="https://labfreed.org/terms/example/BoolAttribute", value=random.choice([True, False])),
                    pyAttribute(key="https://labfreed.org/terms/example/ObjectAttribute", value={'k1':1, 'k2': {'a':'bar', 'b':'foo'}, 'k3': [0,1,2]})
                ]
            ).to_payload_attributes()
            
        return AttributeGroup(key=self._attribute_group_key, 
                              state_of=datetime.now(tz=timezone.utc),
                              attributes=attributes)


data_sources.append(
    DynamicDemoAttributeGroup(attribute_group_key='https://mettorius.com/terms/attribute_group_demo')
    )

transation_data_sources.append(
    DictTranslationDataSource(
        supported_languages={'en', 'fr'},
        data=Terms(
            terms=[
                Term.create("https://mettorius.com/terms/attribute_group_demo", [('en', 'Demo'), ('fr', 'Example')]),
                Term.create("https://labfreed.org/terms/example/TextAttribute", [('en', 'Text Attribute'), ('fr', 'Attribut text')] ),
                Term.create("https://labfreed.org/terms/example/NumericAttribute", [('en', 'Numeric Attribute'), ('fr', 'Attribut numérique')] ),
                Term.create("https://labfreed.org/terms/example/ReferenceAttribute", [('en', 'Reference Attribute'), ('fr', 'Attribut de référence')] ),
                Term.create("https://labfreed.org/terms/example/DateTimeAttribute", [('en', 'Date Attribute'), ('fr', 'Attribut date')] ),
                Term.create("https://labfreed.org/terms/example/BoolAttribute", [('en', 'Boolean Attribute'), ('fr', 'Attribut date')] ),
                Term.create("https://labfreed.org/terms/example/ObjectAttribute", [('en', 'Object Attribute (LAST RESORT)'), ('fr', "Attribut d'objet (DERNIER RECOURS)")] ),
            ]
        )
    )
)




'''
Set up the server
=================
We will create a server app with Flask. 
'''
# It is the servers responsibility to handle authentication. All the labfreed library does is to invoke an object implementing the Authenticator protocol.
# Lets implement this protocol so it accepts BasicAuthentication with credentials "test", "1234"
class DemoAuthenticator: 
    def __call__(self, request: Request) -> bool:
        '''Crude example checking for valid credentials with BasicAuthentication'''
        VALID_CREDENTIALS = {"test":"1234"}
        
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            return False

        try:
            encoded_credentials = auth_header.split(' ', 1)[1]
            decoded = base64.b64decode(encoded_credentials).decode('utf-8')
            user, pw = decoded.split(':', 1)
        except Exception:
            return False

        if not (user in VALID_CREDENTIALS.keys() and VALID_CREDENTIALS.get(user) == pw):
            return False
        
        return True


# create the flask app
app = AttributeServerFactory.create_server_app(
        framework=Webframework.FLASK,
        datasources=data_sources, 
        default_language='en',
        translation_data_sources=transation_data_sources,
        authenticator=DemoAuthenticator()
    )
    
    
# run the flask app.    
if __name__ == '__main__':
    app.run(debug=True)
    
    
''' 
You can now interact with the server on http://127.0.0.1:5000

Use a tool like postman (https://www.postman.com).

First try "http://127.0.0.1:5000/capabilities":
>>>
{
    "supported_languages": [
        "fr",
        "en"
    ],
    "default_language": "en",
    "available_attribute_groups": [
        "https://labfreed.org/attribute_metadata_group",
        "https://mettorius.com/terms/attribute_group_excel",
        "https://mettorius.com/terms/attribute_group_demo"
    ]
}

Now request attributes by posting:
{
  "pac_urls": [
     "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001*59K77LWDX8W" 
   ],
   "language_preferences": ["en", "fr"]
}
Don't forget to add the credentials to the header.

'''
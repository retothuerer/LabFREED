



from datetime import datetime

from flask import Flask
from labfreed.pac_attributes.client.attribute_cache import MemoryAttributeCache
from labfreed.pac_attributes.client.client import AttributeClient, http_attribute_request_default_callback_factory
from labfreed.pac_attributes.pythonic.attribute_server_factory import AttributeServerFactory, NoAuthRequiredAuthenticator
from labfreed.pac_attributes.pythonic.py_attributes import pyAttribute, pyAttributes, pyReference
from labfreed.pac_attributes.pythonic.py_dict_data_source import pyDict_DataSource
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource, Terms, Term
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.trex.pythonic.quantity import Quantity

import threading
from werkzeug.serving import make_server





data_source = pyDict_DataSource(attribute_group_key='ProductionData', 
                            data = {
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(year=2015, month=10, day=1, hour=10, minute=12)),
                                    pyAttribute(key="MaxWeight", values=Quantity(value=100.00, unit='g', log_least_significant_digit=-2)),
                                    pyAttribute(key="CalWeight", values=pyReference('HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002')),
                                    pyAttribute(key="multitext", values=["foo", "bar"])
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(year=2015, month=10, day=1, hour=10, minute=12)),
                                    pyAttribute(key="MaxWeight", values=Quantity(value=100.00, unit='g', log_least_significant_digit=-2)),
                                    pyAttribute(key="CalWeight", values=pyReference('HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002')),
                                    pyAttribute(key="multitext", values=["foo", "bar"])
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12341": pyAttributes([
                                    pyAttribute(key="MfgDate", values=datetime(year=2015, month=10, day=1, hour=10, minute=12)),
                                    pyAttribute(key="MaxWeight", values=Quantity(value=111.00, unit='g', log_least_significant_digit=2))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12342": pyAttributes([
                                    pyAttribute(key="MfgDate", values=datetime(year=2015, month=10, day=1, hour=10, minute=12)),
                                    pyAttribute(key="MaxWeight", values=Quantity(value=100.00, unit='g'))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002": pyAttributes([
                                    pyAttribute(key="NominalWeight", values=Quantity(value=50.00, unit='g'))
                                ])
                                }
                )


data_source_example = pyDict_DataSource(attribute_group_key='https://mettorius.com/terms/attribute_group_example', 
                            data = {
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001": pyAttributes([
                                    pyAttribute(key="https://labfreed.org/terms/example/TextAttribute", value="Bar"),
                                    pyAttribute(key="https://labfreed.org/terms/example/NumericAttribute", value="14.88 mol/L"),
                                    pyAttribute(key="https://labfreed.org/terms/example/ReferenceAttribute", value="HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002"),
                                    pyAttribute(key="https://labfreed.org/terms/example/DateTimeAttribute", value=datetime(year=2015, month=10, day=1, hour=10, minute=12)),
                                    pyAttribute(key="https://labfreed.org/terms/example/BoolAttribute", value=False),
                                    pyAttribute(key="https://labfreed.org/terms/example/ObjectAttribute", value= {'k1':1, 'k2': {'a':'bar', 'b':'foo'}, 'k3': [0,1,2]})
                                ])
                                }
                )

data_source_example_lists = pyDict_DataSource(attribute_group_key='https://mettorius.com/terms/attribute_group_example_lists', 
                            data = {
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001": pyAttributes([
                                    pyAttribute(key="https://labfreed.org/terms/example/TextAttribute", values=["Foo", 
                                                                                                                "Bar"]),
                                    pyAttribute(key="https://labfreed.org/terms/example/NumericAttribute", values=["14.88 mol/L",
                                                                                                                   "201E-3 g"]),
                                    pyAttribute(key="https://labfreed.org/terms/example/ReferenceAttribute", values=["HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002", 
                                                                                                                     "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00001"]),
                                    pyAttribute(key="https://labfreed.org/terms/example/DateTimeAttribute", values= [datetime(year=2015, month=10, day=1, hour=10, minute=12),
                                                                                                                     datetime(year=2016, month=11, day=11, hour=11, minute=22)]),
                                    pyAttribute(key="https://labfreed.org/terms/example/BoolAttribute", values=[True,
                                                                                                                False]),
                                    pyAttribute(key="https://labfreed.org/terms/example/ObjectAttribute", values= [{'k1':1, 'k2': {'a':'bar', 'b':'foo'}, 'k3': [0,1,2]},
                                                                                                                   {'k1':111}]),
                                    pyAttribute(key="https://labfreed.org/terms/example/Mixed", values= ["Foo",
                                                                                                         "14.88 mol/L",
                                                                                                         "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002",
                                                                                                         datetime(year=2015, month=10, day=1, hour=10, minute=12),
                                                                                                         True,
                                                                                                         {'k1':111}])
                                ])
                            }
                )



translation_data_source = DictTranslationDataSource(
                                    supported_languages=                     ["en", "en-US", "fr"],
                                    data= Terms(terms= [
                                        Term.create("MfgDate", [    ("en", "Manufactoring date"),
                                                                    ("en-US", "Manufactoring date"),
                                                                    ("fr", "Date de fabrication")
                                                                    ]
                                        ),
                                        Term.create("MaxWeight", [    ("en", "Maximum weight"),
                                                                     ("fr", "Poids maximal")
                                                                ]
                                        ),
                                        Term.create("CalWeight", [    ("en", "Calibration weight"),
                                                                     ("fr", "Poids calibration")
                                                                ]
                                        ),
                                        Term.create("https://mettorius.com/terms/attribute_group_example", [ ("en", "Example Attribute Group") ] ),
                                        Term.create("https://mettorius.com/terms/attribute_group_example_lists", [ ("en", "Example Attribute Group Lists") ] ),
                                        Term.create("https://labfreed.org/terms/example/TextAttribute", [ ("en", "Text Attribute")]),
                                        Term.create("https://labfreed.org/terms/example/NumericAttribute", [ ("en", "Numeric Attribute")]),
                                        Term.create("https://labfreed.org/terms/example/ReferenceAttribute", [("en", "Reference Attribute")]),
                                        Term.create("https://labfreed.org/terms/example/DateTimeAttribute", [("en", "Date Attribute")]),
                                        Term.create("https://labfreed.org/terms/example/BoolAttribute", [ ("en", "Bool Attribute")]),
                                        Term.create("https://labfreed.org/terms/example/ObjectAttribute", [("en", "Object Attribute (LAST RESORT)")]),
                                        Term.create("https://labfreed.org/terms/example/Mixed", [ ("en", "Mixed List (ACTUALLY NOT ALLOWED)")])
                                    ]
                                    )
                                )


server_app:Flask = AttributeServerFactory.create_server_app(datasources=[data_source, data_source_example, data_source_example_lists], 
                                                  translation_data_sources=[translation_data_source], 
                                                  authenticator= NoAuthRequiredAuthenticator(), 
                                                  default_language="en")

SERVER_URL = "127.0.0.1"
PORT = 5000

class FlaskServerThread(threading.Thread):
    def __init__(self, app, host: str, port: int):
        super().__init__(daemon=True)
        self._server = make_server(host, port, app)
        self._ctx = app.app_context()
        self._ctx.push()

    def run(self):
        self._server.serve_forever()

    def shutdown(self):
        self._server.shutdown()


client = AttributeClient(http_post_callback=http_attribute_request_default_callback_factory(), cache_store=MemoryAttributeCache(), always_use_cached_value_for_minutes=0)
  
def test():
    pac_id = PAC_ID.from_url("HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340")
    pac_id2 = PAC_ID.from_url("HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12341*ABC$TREX/A$T.A:BLUBB")
    server = FlaskServerThread(server_app, SERVER_URL, PORT)
    server.start()
    
    try:
        attribute_groups = client.get_attributes(server_url=f"http://{SERVER_URL}:{PORT}", pac_id=pac_id)
        for ag in attribute_groups:
            print(ag.group_key)
    finally:
        server.shutdown()
        server.join(timeout=2)
    
def test2():
    pac_id = PAC_ID.from_url("HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340")
    pac_id2 = PAC_ID.from_url("HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12341*ABC$TREX/A$T.A:BLUBB")

    server_app.run()
    



if __name__ == "__main__":
    test2()

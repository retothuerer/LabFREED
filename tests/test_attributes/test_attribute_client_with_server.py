



from datetime import datetime
import json
from labfreed.pac_attributes.client.client import AttributeClient
from labfreed.pac_attributes.pythonic.py_attributes import pyAttribute, pyAttributes, pyReference
from labfreed.pac_attributes.server.attribute_data_sources import Dict_DataSource, PACAnalyzerAttributeDataSource, RandomAttributeGroupDataSource
from labfreed.pac_attributes.server.server import AttributeServerRequestHandler
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.trex.pythonic.quantity import Quantity



def in_memory_callback(url: str, attribute_request_body: str) -> tuple[int, str]:
    try:
        resp = request_handler.handle_attribute_request(attribute_request_body)
        return 200, resp
    except Exception as e:
        return 500, str(e)


attribute_client = AttributeClient(http_post_callback=in_memory_callback, cache_store=MemoryAttributeCache())




data_source = Dict_DataSource(attribute_group_key='ProductionData', 
                            data = {
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(year=2015, month=10, day=1, hour=10, minute=12), valid_until='forever'),
                                    pyAttribute(key="MaxWeight", value=Quantity(value=100.00, unit='g', log_least_significant_digit=-2)),
                                    pyAttribute(key="CalWeight", value=pyReference('HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002'))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12341": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(year=2015, month=10, day=1, hour=10, minute=12), valid_until='forever'),
                                    pyAttribute(key="MaxWeight", value=Quantity(value=111.00, unit='g', log_least_significant_digit=2))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12342": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(year=2015, month=10, day=1, hour=10, minute=12), valid_until='forever'),
                                    pyAttribute(key="MaxWeight", value=Quantity(value=100.00, unit='g'))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002": pyAttributes([
                                    pyAttribute(key="NominalWeight", value=Quantity(value=50.00, unit='g'), valid_until='forever')
                                ])
                                }
                )

data_source2 = RandomAttributeGroupDataSource(attribute_group_key="Random", attribute_keys=["Foo", "Bar", "Deadmeat", "Abc"])


data_source3 = PACAnalyzerAttributeDataSource(attribute_group_key="PACAnalyzer")


translation_data_source = DictTranslationDataSource(data=
                                                    {
                                                        "MfgDate": {
                                                                        "en": "Manufactoring date",
                                                                        "en-US": "Manufactoring date",
                                                                        "fr": "Date de fabrication"
                                                                    },
                                                        "MaxWeight": {
                                                                        "en": "Maximum weight",
                                                                        "fr": "Poids maximal"
                                                                    },
                                                        "CalWeight": {
                                                                        "en": "Calibration weight",
                                                                        "fr": "Poids calibration"
                                                                    }
                                                        
                                                    }
                                                )

test_handler = AttributeServerRequestHandler(data_sources=[data_source], translation_data_source=translation_data_source)
def local_no_network_callback(url:str, attribute_request_body=str, params:dict=None):
    return test_handler.handle_attribute_request(attribute_request_body)

client = AttributeClient(http_post_callback=local_no_network_callback)

pac_id = PAC_ID.from_url("HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340")
pac_id2 = PAC_ID.from_url("HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12341*ABC$TREX/A$T.A:BLUBB")

  
def test_():
    attribute_groups = client.get_attributes(server_url="", pac_id=pac_id)
    ...
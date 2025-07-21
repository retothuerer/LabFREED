from datetime import datetime, timezone
from labfreed.pac_attributes.python_convenience import pyAttribute, pyAttributes, pyReference
from labfreed.pac_attributes.server.attribute_data_sources import Dict_DataSource, PACAnalyzerAttributeDataSource, RandomAttributeGroupDataSource
from labfreed.pac_attributes.server.server_factory import AttributeServerFactory, Webframework
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource
from labfreed.trex.python_convenience.quantity import Quantity


data_source0 = Dict_DataSource(attribute_group_key='MetaData', 
                            data = {
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340": pyAttributes([
                                    pyAttribute(key="DisplayName", value="My Balance")
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345/DEMO": pyAttributes([
                                    pyAttribute(key="DisplayName", value="My Second Balance")
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345/EXAMPLE": pyAttributes([
                                    pyAttribute(key="DisplayName", value="My Example Balance")
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12341": pyAttributes([
                                    pyAttribute(key="DisplayName", value="Balance in the Cellar")
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002": pyAttributes([
                                    pyAttribute(key="DisplayName", value="Calibration Weight PRN003")
                                ])
                                
                                }
)

data_source1 = Dict_DataSource(attribute_group_key='ProductionData', 
                            data = {
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(2015, 10, 1, 10, 12, tzinfo=timezone.utc), valid_until='forever'),
                                    pyAttribute(key="MaxWeight", value=Quantity(value=100.00, unit='g', log_least_significant_digit=-2))                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345/DEMO": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(2015, 10, 5, hour=10, minute=12, tzinfo=timezone.utc), valid_until='forever'),
                                    pyAttribute(key="MaxWeight", value=Quantity(value=100.00, unit='g', log_least_significant_digit=-2))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12346/EXAMPLE": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(2015, 10, 5, hour=10, minute=12, tzinfo=timezone.utc), valid_until='forever'),
                                    pyAttribute(key="MaxWeight", value=Quantity(value=100.00, unit='g', log_least_significant_digit=-2))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12341": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(2015, 10, 1, hour=10, minute=12, tzinfo=timezone.utc), valid_until='forever'),
                                    pyAttribute(key="MaxWeight", value=Quantity(value=111.00, unit='g', log_least_significant_digit=2))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12342": pyAttributes([
                                    pyAttribute(key="MfgDate", value=datetime(2015, 10, 1, hour=10, minute=12, tzinfo=timezone.utc), valid_until='forever'),
                                    pyAttribute(key="MaxWeight", value=Quantity(value=100.00, unit='g'))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002": pyAttributes([
                                    pyAttribute(key="NominalWeight", value=Quantity(value=50.00, unit='g'), valid_until='forever')
                                ])
                                
                                }
                )

data_source2 = Dict_DataSource(attribute_group_key='Maintenance', 
                            data = {
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12340": pyAttributes([
                                    pyAttribute(key="CalWeight", value=pyReference('HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002')),
                                    pyAttribute(key="CalDate", value=datetime(2025, 7, 20, tzinfo=timezone.utc), valid_until=datetime(2025,8,20, tzinfo=timezone.utc)),
                                    pyAttribute(key="DailyCheckResult", value="OK", observed_at=datetime(2025, 8, 20, tzinfo=timezone.utc), valid_until=datetime(2025,7,20, tzinfo=timezone.utc))
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12346/EXAMPLE": pyAttributes([
                                    pyAttribute(key="CalWeight", value=pyReference('HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002')),
                                    pyAttribute(key="CalDate", value=datetime(2025, 7, 20, tzinfo=timezone.utc), valid_until=datetime(2025,8,20, tzinfo=timezone.utc)),
                                    pyAttribute(key="DailyCheckResult", value="OK", observed_at=datetime(2025, 7, 20, tzinfo=timezone.utc), valid_until=datetime(2025,7,20, tzinfo=timezone.utc))
                                ])
                            }
)

data_source3 = RandomAttributeGroupDataSource(attribute_group_key="Random", attribute_keys=["Foo", "Bar", "Deadmeat", "Abc"])


data_source4 = PACAnalyzerAttributeDataSource(attribute_group_key="PACAnalyzer")


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

app = AttributeServerFactory.create_server_app(datasources=[data_source0, data_source1, data_source2, data_source3, data_source4], 
                                               translation_data_source=translation_data_source,
                                               framework=Webframework.FLASK)
    
    
if __name__ == '__main__':
    app.run(debug=True)
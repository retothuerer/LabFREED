from datetime import datetime, timezone
import os
from labfreed_extended.pac_attributes.server.attribute_server_factory import AttributeServerFactory, Webframework
from labfreed_extended.pac_attributes.server.excel_attribute_data_source import ExcelAttributeDataSource
from labfreed_extended.pac_attributes.server.mock_attribute_data_sources import PACAnalyzerAttributeDataSource, RandomAttributeGroupDataSource
from labfreed.utilities.translations import Translation, TranslationsForOntology, Term
from labfreed.pac_attributes.python_convenience.py_attributes import pyAttribute, pyAttributes, pyReference
from labfreed.pac_attributes.server.attribute_data_sources import Dict_DataSource
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource
from labfreed.trex.python_convenience.quantity import Quantity



data_source0 = Dict_DataSource(attribute_group_key='MetaData', 
                               include_extensions=False,
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
                               include_extensions=False,
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
                               include_extensions=False,
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

fp = os.path.join(os.path.dirname(__file__), 'excel_data.xlsx')
data_source5 = ExcelAttributeDataSource(attribute_group_key="Excel", file_path=fp, include_extensions=False)


data_source_example = Dict_DataSource(attribute_group_key='Example', 
                                      include_extensions=False,
                            data = {
                                "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001/EXAMPLE": pyAttributes([
                                    pyAttribute(key="Text", value="Foo", observed_at=datetime(2025, 8, 20, tzinfo=timezone.utc), valid_until=datetime(2025,7,20, tzinfo=timezone.utc)),
                                    pyAttribute(key="Numeric", value=Quantity(value=123.45, unit='m')),
                                    pyAttribute(key="Reference", value=pyReference('HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002')),
                                    pyAttribute(key="DateTime", value=datetime(2025, 7, 20, tzinfo=timezone.utc)),
                                    pyAttribute(key='Bool', value=True),
                                    pyAttribute(key='Object', value={'k1':1, 'k2': {'a':'bar', 'b':'foo'}, 'k3': [0,1,2]})
                                    
                                ]),
                                "HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002": pyAttributes([
                                    pyAttribute(key="Text", value="Bar", )
                                ]),
                            }
)




data=TranslationsForOntology(
        ontology="default",
        terms=[
            Term(
                key="MfgDate",
                translations=[
                    Translation(language_code="en", text="Manufactoring date"),
                    Translation(language_code="en-US", text="Manufactoring date"),
                    Translation(language_code="fr", text="Date de fabrication"),
                ]
            ),
            Term(
                key="MaxWeight",
                translations=[
                    Translation(language_code="en", text="Maximum weight"),
                    Translation(language_code="fr", text="Poids maximal"),
                ]
            ),
            Term(
                key="CalWeight",
                translations=[
                    Translation(language_code="en", text="Calibration weight"),
                    Translation(language_code="fr", text="Poids calibration"),
                ]
            ),
            Term(
                key="DisplayName",
                translations=[
                    Translation(language_code="en", text="Display Name "),
                    Translation(language_code="fr", text="Nom visuel"),
                ]
            ),
            Term.create('Example', [('en', 'Example'), ('fr', 'Exemple')] ),
            Term.create('Numeric', [('en', 'Numeric Attribute'), ('fr', 'Attribut numérique')] ),
            Term.create('Reference', [('en', 'Reference Attribute'), ('fr', 'Attribut de référence')] ),
            Term.create('DateTime', [('en', 'Date Attribute'), ('fr', 'Attribut date')] ),
            Term.create('Text', [('en', 'Text Attribute'), ('fr', 'Attribut text')] ),
            Term.create('Object', [('en', 'Object Attribute (LAST RESORT)'), ('fr', "Attribut d'objet (DERNIER RECOURS)")] ),
        ]
    )
#print(data.model_dump_json(indent=2))
default_translation_data_source = DictTranslationDataSource(
    onthology="default",
    data = data
)


app = AttributeServerFactory.create_server_app(datasources=[data_source0, data_source1, data_source2, data_source3, data_source4, data_source5, data_source_example], 
                                               translation_data_sources=[default_translation_data_source],
                                               framework=Webframework.FLASK)
    
    
if __name__ == '__main__':
    app.run(debug=True)
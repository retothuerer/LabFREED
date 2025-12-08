
from datetime import datetime, timedelta, timezone
import os
import random

from labfreed.pac_attributes.well_knonw_attribute_keys import MetaAttributeKeys
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_cat.predefined_categories import Material_Device

from labfreed.pac_attributes.pythonic.py_dict_data_source import pyDict_DataSource
from labfreed.pac_attributes.pythonic.py_attributes import pyAttributes, pyAttribute, pyReference, pyResource
from labfreed.pac_attributes.server.translation_data_sources import DictTranslationDataSource
from labfreed.trex.pythonic.quantity import Quantity

from labfreed.utilities.translations import Terms, Term


from labfreed.labfreed_extended.pac_issuer_lib.lib.attribute import DynamicDemoAttributeGroup, product_number_from_pac_url, is_device

data_sources = []
translation_data_sources = []

static_url_prefix = "http://127.0.1:5051/mettorius/static" if os.environ.get('DEV') else "https://pbue-app-labfreed-issuer-cwe-cag3hzgvcua2apem.westeurope-01.azurewebsites.net/mettorius/static" #"https://webtools.labfreed.org/mettorius/static"

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

safety_ds = pyDict_DataSource(
    attribute_group_key="https://labfreed.org/safety",
    include_extensions=False,
    data={
        "HTTPS://PAC.METTORIUS.COM/-MS/BALCLEAN": pyAttributes([
            pyAttribute(key=MetaAttributeKeys.DISPLAYNAME.value, value="Bal Clean Safety Information"),
            pyAttribute(key="https://labfreed.org/ghs/signal-word", value="Danger"),
            pyAttribute(key="https://labfreed.org/ghs/h/H225", value="Highly flammable liquid and vapour"),
            pyAttribute(key="https://labfreed.org/ghs/h/EUH066", value="Repeated exposure may cause skin dryness or cracking"),
            pyAttribute(key="https://labfreed.org/ghs/p/P210", value="Keep away from heat, sparks, open flames and hot surfaces — No smoking"),
            pyAttribute(key="https://labfreed.org/ghs/pictogram/GHS02", value=pyResource("https://www.unece.org/fileadmin/_migrated/RTE/RTEmagicC_160a419206.gif.gif"))
        ])
    }
)

data_sources.append(safety_ds)


translation_data_sources.append(
    DictTranslationDataSource(
        supported_languages={'en'},
        data=Terms(
                terms=[
                    Term.create("https://labfreed.org/ghs/signal-word", [('en', 'Signal Word')]),
                    Term.create("https://labfreed.org/ghs/h/H225", [('en', 'H225')]),
                    Term.create("https://labfreed.org/ghs/h/EUH066", [('en', 'EUH066')]),
                    Term.create("https://labfreed.org/ghs/p/P210", [('en', 'P210')]),
                    Term.create("https://labfreed.org/ghs/pictogram/GHS02", [('en', 'GHS02')])
                ]
            )
    )
)







supplier_meta_data_ds = pyDict_DataSource(
    attribute_group_key="https://labfreed.org/supplier-data",
    pac_to_key=product_number_from_pac_url,
    data={
        "BAL500": pyAttributes([
            pyAttribute(key=MetaAttributeKeys.IMAGE.value, value=pyResource(f"{static_url_prefix}/BAL500.png")),
            pyAttribute(key="https://mettorius.com/terms/cleaning-agent", value=pyReference("HTTPS://PAC.METTORIUS.COM/-MS/BALCLEAN"))
        ]),
        "BALCLEAN": pyAttributes([
            pyAttribute(key=MetaAttributeKeys.IMAGE.value, value=pyResource(f"{static_url_prefix}/bal-clean.png")),
            pyAttribute(key=MetaAttributeKeys.DISPLAYNAME.value, value="Bal Clean - The best balance cleaner"),
            pyAttribute(key='HTTPS://PAC.METTORIUS.COM/-DS/BOILING-POINT/DEFINITION', value=Quantity(value=307, unit='K'))
        ]),
        "CALWEIGH": pyAttributes([
            pyAttribute(key=MetaAttributeKeys.IMAGE.value, value=pyResource(f"{static_url_prefix}/cal-weights.png"))
        ]),      
        "HTTPS://PAC.METTORIUS.COM/-DS/DEF/BP": pyAttributes([
                pyAttribute(key='https://doi.org/10.1351/goldbook.P04819', value=Quantity(value=500, unit='mbar')),
                pyAttribute(key='abc', value="AAAAAA")
            ]),
        
    }
)
data_sources.append(supplier_meta_data_ds)



my_definitions_ds =  pyDict_DataSource(
    attribute_group_key="https://mettorius.com/definitions",
    data={
        "HTTPS://PAC.METTORIUS.COM/-DS/BOILING-POINT/DEFINITION": pyAttributes([
                pyAttribute(key=MetaAttributeKeys.DISPLAYNAME.value, value="Boilingpoint 500 mbar"),
                pyAttribute(key='https://doi.org/10.1351/goldbook.P04819', value=Quantity(value=500, unit='mbar'))
            ]),
        
    }
)
data_sources.append(my_definitions_ds)

translation_data_sources.append(
    DictTranslationDataSource(
        supported_languages={'en'},
        data=Terms(
                terms=[
                    Term.create("https://doi.org/10.1351/goldbook.P04819", [('en', 'Temperature')]),
                    Term.create("HTTPS://PAC.METTORIUS.COM/-DS/BOILING-POINT/DEFINITION", [('en', 'Boilingpoint 500 mbar')])
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


def is_attribute_demo(pac_url):
    return pac_url=="HTTPS://PAC.ATTRIBUTE.DEMO/-MD/A/B"
        
ds = DynamicDemoAttributeGroup(
    attribute_group_key='https://mettorius.com/terms/attribute_group_demo',
    data = [
        ("https://labfreed.org/terms/example/TextAttribute",                random.choice(["Foo", "Bar"]),                                                                  [('en', 'Text Attribute'), ('fr', 'Attribut text')]),
        ("https://labfreed.org/terms/example/NumericAttribute",             Quantity(value=round(random.uniform(0, 100), 2), unit=random.choice(["m", "kg", "mol/L"])),     [('en', 'Numeric Attribute'), ('fr', 'Attribut numérique')]),
        ("https://labfreed.org/terms/example/ReferenceAttribute",           pyReference("HTTPS://PAC.METTORIUS.COM/-MD/CALWEIGH/A00002"),                                   [('en', 'Reference Attribute'), ('fr', 'Attribut de référence')]),
        ("https://labfreed.org/terms/example/DateTimeAttribute",            datetime.now(tz=timezone.utc),                                                                  [('en', 'Date Attribute'), ('fr', 'Attribut date')] ),
        ("https://labfreed.org/terms/example/BoolAttribute",                random.choice([True, False]),                                                                   [('en', 'Boolean Attribute'), ('fr', 'Attribut date')]),
        ("https://labfreed.org/terms/example/ObjectAttribute",              {"k1": 1, "k2": {"a": "bar", "b": "foo"}, "k3": [0, 1, 2]},                                     [('en', 'Object Attribute (LAST RESORT)'), ('fr', "Attribut d'objet (DERNIER RECOURS)")])
    ],
    pac_filter_predicate= is_attribute_demo
)

data_sources.append(ds)
translation_data_sources.append(ds.translations)




def is_BAL500(pac_url):
    pac_cat = PAC_CAT.from_url(pac_url)
    if not isinstance(pac_cat, PAC_CAT):
        return False
    cat: Material_Device = pac_cat.get_category("-MD")
    return  (cat and cat.model_number == "BAL500")




ds = DynamicDemoAttributeGroup(
    attribute_group_key='https://labfreed.com/terms/lifecycle',
    data = [
        ("https://labfreed.org/terms/lifecycle/end-of-life",                "Support for this instrument will end soon. Need a new one. Contact our sales rep.",      []  ),
        ("https://labfreed.org/terms/lifecycle/IQOQ-due-date",             datetime.today() + timedelta(days=random.randint(10, 30)),                           [])
    ],
    pac_filter_predicate= is_device
)

data_sources.append(ds)
translation_data_sources.append(ds.translations)



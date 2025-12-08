import os
from pathlib import Path
from typing import Any

from flask import Blueprint
from labfreed.labfreed_extended.pac_issuer_lib.app_factory import IssuerFlaskAppFactory, NavItem, PacInfoExtender, SiteMeta, attribute_data_from_module


from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo

PAC_ID_BASE = 'HTTPS://PAC.METTORIUS.COM'
resolver_macros = { "METTORIUS_HOME": "https://mettorius.com", 
                    "BASE_URL":os.environ.get("WEBSITE_HOSTNAME") # for Azure webapp this gives us the url the site runs on. Adapt if needed
                    }

site_meta_data = SiteMeta(site_title="PAC-Info",
                          site_author="Mettorius GmBH",
                          site_description="Landing page when a PAC-ID is opened in a generic browser.",
                          nav_items= [
                                NavItem(name="Shop", href="https://www.mettorius.com/shop", icon_filename="shop.svg")       
                            ]
                          )

import examples.pac_mettorius_com.attribute_datasources as mettorius 
attribute_data = attribute_data_from_module(mettorius, default_language='en')

class MettoriusPACInfoExtended(PacInfo):   
    has_dummy_action:bool|None = None
    
class MettoriusPacInfoExtender(PacInfoExtender):
    
    @staticmethod
    def extend(pac_info: PacInfo) -> Any:
        out = MettoriusPACInfoExtended.model_construct(**pac_info.model_copy().__dict__)
        
        # dummy
        out.has_dummy_action = pac_info.get_action_by_intent('dummy')
                          
        return out

path_to_custom_resources=Path(__file__).parent

app = IssuerFlaskAppFactory.create_app(
    issuer='METTORIUS.COM',
    site_meta=site_meta_data,
    attribute_data=attribute_data,
    path_to_custom_resources=path_to_custom_resources,
    pac_info_extender= MettoriusPacInfoExtender(),
    resolver_macros = resolver_macros,
    use_issuer_resolver_config = False
)





bp_add_on = Blueprint('add_on_blueprint', __name__, url_prefix='/add_on')

@bp_add_on.get('/', strict_slashes=False)
def mettorius_company_mission():            
    return "We strive to deliver the best devices, for a reasonable price. And the best of all: They all come with native LabFREED support"

app.register_blueprint(bp_add_on)



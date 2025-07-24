import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from labfreed.pac_attributes.client.client import AttributeClientDefaultFactory
from labfreed_extended.app.pac_info import PacInfo
from labfreed_extended.utilities.formatted_print import StringIOLineBreak
from labfreed.pac_attributes.python_convenience.py_attributes import pyAttributes
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.resolver import PAC_ID_Resolver, cit_from_str
from labfreed.pac_id_resolver.services import ServiceGroup
from labfreed.utilities.translations import Term, Translation

        



class Labfreed_App_Infrastructure():
    def __init__(self, markup = 'rich', language='en'):
        self.http_client = requests.Session()
        
        self.resolver = PAC_ID_Resolver()
        
        self.attribute_client = AttributeClientDefaultFactory.create_attribute_client()
        
        translation_cache=self.attribute_client.translation_cache_store
        translation_cache.update('local', Term(key='Deadmeat', translations=[ Translation(language_code='en', text="Dead Meat"), 
                                                                               Translation(language_code='fr', text="Viande Morte")
                                                                              ]
                                               )
        )
        translation_cache.update('local', Term(key='MfgDate',  translations=[Translation.create('en', "Manufacturing Date")]))
        translation_cache.update('local', Term.create(key='CalDate',  translations=[('en', "HUIIII"), ('fr', "uiiiiih")]) )
        translation_cache.update('local', Term.create('MaxWeight',  [('en', "Maximum weight"), ('fr', "Poids maximal")]) )
        
        self.translation_cache = translation_cache
        
        self.language = language
        
       
        
    def add_cit(self, cit:str):
        cit = cit_from_str(cit)
        if not cit:
            raise ValueError('the cit could not be parsed. Neither as v1 or v2')
        self.resolver._cits.append(cit)
        
        
    def process_pac(self, pac_url, markup=None):
        if not isinstance(pac_url, PAC_ID):
            pac = PAC_ID.from_url(pac_url)
        else:
            pac = pac_url
        service_groups = self.resolver.resolve(pac, check_service_status=False)
        
        pac_info = PacInfo(pac_id=pac)
        
        if dn := pac.get_extension('N'):
            pac_info.display_name = dn.display_name
               
               
        # update service states
        (sg.update_states() for sg in service_groups)
               
        # Services
        sg_user_handovers = []
        for sg in service_groups:
            user_handovers = [s  for s in sg.services if s.service_type == 'userhandover-generic']
            
            if user_handovers:
                sg_user_handovers.append(ServiceGroup(origin=sg.origin, services=user_handovers))
        pac_info.user_handovers = sg_user_handovers
        
        # Attributes
        attribute_groups = []
        for sg in service_groups:  
            attributes_urls = [s.url  for s in sg.services if s.service_type == 'attributes-generic']
            for url in attributes_urls:
                ags = self.attribute_client.get_attributes(url, pac_id=pac.to_url(include_extensions=False))
                attribute_groups.extend(ags)
        pac_info.attributes = attribute_groups
              
        return pac_info
    
    
    def print_pac_info(self, pac_info:'PacInfo', markup:str='rich'):
        
        printout = StringIOLineBreak(markup=markup)
        
        printout.write(f"for {pac_info.pac_url}")
        
        printout.title1("Info")
        printout.key_value("Display Name", pac_info.display_name)
        
        if isinstance(pac_info.pac_id, PAC_CAT):
            printout.title1("Categories")
            for c in pac_info.pac_id.categories:
                category_name = c.__class__.__name__
                printout.title2(category_name)
                for k,v in c.segments_as_dict().items():
                    printout.key_value(k, v)
                
                    
        printout.title1("Services")
        for sg in pac_info.user_handovers:           
            printout.title2(f"(from {sg.origin})")
            for s in sg.services:
                printout.link(s.service_name, s.url)          
        
        
        printout.title1("Attributes")
        for ag in pac_info.attributes:  
            printout.title2(f'{ag.key} (from {ag.origin})')
            attributes = pyAttributes.from_payload_attributes(ag.attributes)
            for k, v in attributes.items():
                print(f'{k}: {self.get_display_text(ag.origin, k)}           :: {v.value}  ')
                printout.key_value(self.get_display_text(ag.origin, k), v.value)
      
        out =  printout.getvalue()

        return out
    
    

    def get_display_text(self, ontology, key):
        ''' finds the text for the given key'''
        if not (t := self.translation_cache.get('local', key) or self.translation_cache.get(ontology, key) ):
            return key
        t:Term      
        language_fallback_lvl1 = self.language.split('-')[0] #fall back to the language without region
        language_fallback_lvl2 = 'en'
        fallback_lvl3 = key
        return t.in_language(self.language) or t.in_language(language_fallback_lvl1) or t.in_language(language_fallback_lvl2) or fallback_lvl3
    
    


    
    def update_user_handover_states(self, services, session:requests.Session = None):
        '''Triggers each service to check if the url can be reached'''
        if not _has_internet_connection():
            raise ConnectionError("No Internet Connection")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(s.check_service_status, session=session) for s in services]
            for _ in as_completed(futures):
                pass  # just wait for all to finish
            
            
def _has_internet_connection():
    try:
        requests.get("https://1.1.1.1", timeout=3)
        return True
    except requests.RequestException:
        return False
                
                
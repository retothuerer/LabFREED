
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from typing import Self, TextIO
from pydantic import BaseModel, Field, RootModel
import requests
import rich
from concurrent.futures import ThreadPoolExecutor, as_completed


from labfreed.labfreed_infrastructure import LabFREED_ValidationError
from labfreed.pac_attributes.api_data_models.response import AttributeBase
from labfreed.pac_attributes.client.client import AttributeClient
from labfreed.pac_attributes.python_convenience import pyAttributes
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.resolver import PAC_ID_Resolver, cit_from_str
from labfreed.pac_id_resolver.services import ServiceGroup
from labfreed.trex.python_convenience import pyTREX
from labfreed.trex.python_convenience.data_table import DataTable


def print_attribute_groups(attribute_groups: list[AttributeBase]):
    for ag in attribute_groups:
        print(pac.to_url()+":")
        print(ag.model_dump_json(indent=2))
        
        
class Demo_Labfreed_App_Infrastructure():
    def __init__(self, markup = 'none'):
        self.http_client = requests.Session()
        
        self.resolver = PAC_ID_Resolver()
        self.attribute_client = AttributeClient()
        
        
        
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
                
                

     
        
        

    
class PacInfo(BaseModel):
    pac_id:PAC_ID
    display_name:str|None = None
    user_handovers: list[ServiceGroup] = Field(default_factory=list)
    attributes:pyAttributes = Field(default_factory=list)
    
    @property
    def pac_url(self):
        return self.pac_id.to_url(include_extensions=False)
    
    @property
    def main_category(self):
        if isinstance(self.pac_id, PAC_CAT):
            return self.pac_id.categories[0]
        else:
            return None
        
    @property
    def attached_data(self):
        return self.pac_id.get_extension_of_type('TREX')
    
    @property
    def summary(self):
        return self.pac_id.get_extension('SUM')
        
        
    
    
    def __str__(self, markup:str='rich'):                
        printout = StringIOLineBreak(markup=markup)
        
        printout.write(f"for {self.pac_url}")
        
        printout.title1("Info")
        printout.key_value("Display Name", self.display_name)
        
        if isinstance(self.pac_id, PAC_CAT):
            printout.title1("Categories")
            for c in self.pac_id.categories:
                category_name = c.__class__.__name__
                printout.title2(category_name)
                for k,v in c.segments_as_dict().items():
                    printout.key_value(k , v)
                
                    
        printout.title1("Services")
        for sg in self.user_handovers:           
            printout.title2(f"(from {sg.origin})")
            for s in sg.services:
                printout.link(s.service_name, s.url)          
        
        
        printout.title1("Attributes")
        for ag in self.attributes:  
            printout.title2(f'{ag.key} (from {ag.origin})')
            attributes = pyAttributes.from_payload_attributes(ag.attributes)
            for k, v in attributes.items():
                printout.key_value(k, v.value)
      
        out =  printout.getvalue()

        return out
    



            
            
class StringIOLineBreak(StringIO):
            def __init__(self, *args, markup=None,  **kwargs):
                self._markup = markup
                super().__init__(*args, **kwargs)
            
            def write(self, s:str):
                s = s + '\n'
                super().write(s)
                
            def write_indented(self, s:str):
                s = '    ' + s + '\n'
                super().write(s)
                
            def title1(self, s):
                if self._markup == 'rich':
                    s = f'[bold][underline]{s}[/underline][/bold]'
                elif self._markup == 'kivy':
                    s = f'[b][u]{s}[/u][/b]'
                self.new_section()
                self.write(s)  
                
            def title2(self, s):
                if self._markup == 'rich':
                    s = f'[bold]{s}[/bold]'
                elif self._markup == 'kivy':
                    s = f'[b]{s}[/b]'
                self.new_paragraph()
                self.write(s) 
                
            def key_value(self, k, v):
                if not k:
                    self.write_indented(v)
                    return
                    
                if self._markup == 'rich':
                    s = f'[bold]{k}[/bold]:  {v}'
                elif self._markup == 'kivy':
                    s = f'[b]{k}[/b]:  {v}'
                self.write_indented(s)
                
            def link(self, s, link):
                if self._markup == 'rich':
                    s = f'[bold]{s}[/bold]:  [link={link}]{link}[/link] '
                elif self._markup == 'kivy':
                    s = f'[b]{s}[/b]:  [ref={link}]{link}[/ref]'
                self.write_indented(s)
                
            
            def new_paragraph(self):
                super().write('\n')    
            
            def new_section(self):
                super().write('\n\n')
        
        
            
demo_cit ='''
origin: DEMO

cit:
- if: $.categories[?(@.key == "-MD")]
  entries:
  - service_type: attributes-generic
    service_name: Demo Attributes
    application_intents:
    - attributes
    template_url: http://127.0.0.1:5000
'''      
            
if __name__ == "__main__":
    app = Demo_Labfreed_App_Infrastructure()
    app.add_cit(demo_cit)
    
    while True:
        print('\n\n============================')
        user_input = input(">>> ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        
        if not user_input or user_input == 'demo':
            pac_url = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345/DEMO*59K77LWDX8W'

        else:
            try:
                pac = PAC_ID.from_url(user_input)
                pac_url = user_input
            except LabFREED_ValidationError as e:
                print('Invalid input')
                     
        pac_info = app.process_pac(pac_url, markup='rich')
        rich.print(str(pac_info))

        
        
        
    
          
        
        
        
    
import requests
import rich

from labfreed.labfreed_infrastructure import LabFREED_ValidationError
from labfreed.pac_attributes.client.client import AuthenticationError
from labfreed.labfreed_extended.app.app_infrastructure import Labfreed_App_Infrastructure
from labfreed.pac_id.pac_id import PAC_ID

 
            
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
    http_client = requests.Session()
    http_client.auth = ('test', '1234')
    app = Labfreed_App_Infrastructure(language_preferences='en', http_client=http_client)
    app.add_cit(demo_cit)
    
    state = 'request-pac-input'
    
    while True:
        
        if state == 'request-pac-input':
            print('\n\n============================')
            user_input = input(">>> ").strip()
            if user_input.lower() in ("exit", "quit"):
                break
            
            if not user_input or user_input == 'demo':
                pac_url = 'HTTPS://PAC.METTORIUS.COM/-MD/240:BAL500/21:000001/K:V*59K77LWDX8W'

            else:
                try:
                    pac = PAC_ID.from_url(user_input)
                    pac_url = user_input
                except LabFREED_ValidationError as e:
                    print('Invalid input. Input must be a PAC-ID. (e.g. ) "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001*59K77LWDX8W"')
                    continue
            
            try:      
                pac_info = app.process_pac(pac_url, markup='rich')
                rich.print(pac_info.format_for_print('rich'))
            except AuthenticationError as e:
                state = 'request-credentials-input'
                
        elif state == 'request-credentials-input': 
            print('Need to authenticate. Enter credentials, e.g. "test;1234" failed.')
            user_input = input(">>> ").strip()
            try:
                nm, pw = user_input.split(';')
                app._http_client.auth = (nm, pw)
                state = 'request-pac-input' 
            except Exception as e:
                continue

        
        
        
    
          
        
        
        
    
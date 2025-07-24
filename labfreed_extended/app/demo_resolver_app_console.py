import rich

from labfreed.labfreed_infrastructure import LabFREED_ValidationError
from labfreed.pac_attributes.api_data_models.response import AttributeBase
from labfreed_extended.app.app_infrastructure import Labfreed_App_Infrastructure
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
    app = Labfreed_App_Infrastructure(language='fr-CH')
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
        rich.print(app.print_pac_info(pac_info))

        
        
        
    
          
        
        
        
    
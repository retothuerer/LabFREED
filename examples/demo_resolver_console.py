from pathlib import Path

from labfreed.pac_id_resolver.resolver import PAC_ID_Resolver, load_cit

def main():
    # Get my resolver config
    resolver_config = load_cit(Path(__file__).resolve().with_name('resolver_config_demo.yaml'))
    # set up resolver
    resolver = PAC_ID_Resolver(resolver_configs=[resolver_config])
    
    # define how to handle pac-ids
    def resolve_and_print(pac_id:str):
        service_groups = resolver.resolve(pac_id, check_service_status=False)
        for sg in service_groups:
            sg.print()
            
    # run loop, which asks for console input
    run_console_input(resolve_and_print)
    
  
    
from labfreed.labfreed_infrastructure import LabFREED_ValidationError  # noqa: E402
def run_console_input(resolve_callback):
    while True:
        print('\n\n============================')
        user_input = input(">>> ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        
        if not user_input or user_input == 'demo':
            pac_url = 'HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001*59K77LWDX8W'
        else:
            pac_url = user_input
    
        try:
            resolve_callback(pac_url)
        except LabFREED_ValidationError as e:
            print('Invalid input. Input must be a PAC-ID. (e.g. ) "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/000001*59K77LWDX8W"')
            continue
        
        
if __name__ == "__main__":
    main() 
    
    
            

        


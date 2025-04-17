from functools import cache
import json
from pathlib import Path




@cache
def unece_units() -> list[dict]:
    p = Path(__file__).parent / 'UneceUnits.json'
    with open(p) as f:
        l = json.load(f)
    return l

@cache
def unece_unit_codes():
    codes= [u.get('commonCode') for u in unece_units() if u.get('state') == 'ACTIVE']
    return codes


def unece_unit(unit_code):
    unit =  [u for u in unece_units() if u['commonCode'] == unit_code]
    if len(unit) == 0:
        return None
    else:
        return unit[0]
    
def unit_symbol(unit:dict) ->str:
    return unit.get('symbol')

def unit_name(unit:dict) ->str:
    return unit.get('name')



# def check_compatibility_unece_quantities():
#     unece = unece_units()
#     print(f'Number of units in file: {len(unece)}')
    
#     failed = list()
#     success = list()
#     for u in unece:
#         if u.get('state') ==  'ACTIVE':
#             try:
#                 if not u.get('symbol'):
#                     assert False
#                 u.get('name')  
#                 validate_unit(u.get('symbol'))
#                 success.append(u)
#             except AssertionError:
#                 failed.append(u)
#         else:
#             pass
        
    
    
#     print('[blue] FAILED [/blue]')
#     for u in failed:
#         print(f'{u.get('commonCode')}: {u.get('name')}')
    
#     print('[yellow] SUCCESSFUL [/yellow]')
#     for u in success:
#         print(u)
        
#     print(f'{len(failed)} / {len(unece)} failed to convert')
        

        
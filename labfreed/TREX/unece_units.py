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


# def quantity_from_UN_CEFACT(value:str, unit_UN_CEFACT) -> UnitQuantity:
#     """ 
#     Maps units from https://unece.org/trade/documents/revision-17-annexes-i-iii
#     to an object of the quantities library https://python-quantities.readthedocs.io/en/latest/index.html 
#     """
#     # cast to numeric type. try int first, which will fail if string has no decimals.
#     # nothing to worry yet: try floast next. if that fails the input was not a str representation of a number
#     try:
#         value_out = int(value)
#     except ValueError:
#         try: 
#             value_out = float(value)
#         except ValueError as e:
#             raise Exception(f'Input {value} is not a str representation of a number') from e
        
#     d = {um[0]: um[1] for um in unit_map}
    
#     unit = d.get(unit_UN_CEFACT)
#     if not unit:
#         raise NotImplementedError(f"lookup for unit {unit} not implemented")
#     out = UnitQuantity(data=value_out, unit_name=unit.name, unit_symbol=unit.symbol)

#     return out



# def quantity_to_UN_CEFACT(value:UnitQuantity ) -> Tuple[int|float, str]:    
#     d = {um[1].symbol: um[0] for um in unit_map}
    
#     unit_un_cefact = d.get(value.unit_symbol)
#     if not unit_un_cefact:
#         raise NotImplementedError(f"lookup for unit {value.unit_symbol} not implemented")
#     return value.data, unit_un_cefact
    
    



def check_compatibility_unece_quantities():
    unece = get_unece_units()
    print(f'Number of units in file: {len(unece)}')
    
    failed = list()
    sucess = list()
    for u in unece:
        if u.get('state') ==  'ACTIVE':
            try:
                if not u.get('symbol'):
                    assert False
                u.get('name')  
                validate_unit(u.get('symbol'))
                sucess.append(u)
            except AssertionError as e:
                failed.append(u)
        else:
            pass
        
    
    
    print('[blue] FAILED [/blue]')
    for u in failed:
        print(f'{u.get('commonCode')}: {u.get('name')}')
    
    print('[yellow] SUCCESSFUL [/yellow]')
    for u in sucess:
        print(u)
        
    print(f'{len(failed)} / {len(unece)} failed to convert')
        

        
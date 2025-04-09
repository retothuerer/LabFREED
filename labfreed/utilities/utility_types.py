from pydantic import BaseModel

from labfreed.TREX.unece_units import unece_units           
                

class Unit(BaseModel):
    name: str
    symbol: str


class Quantity(BaseModel):
    value:int|float
    unit: Unit
      
    def __str__(self):
        unit_symbol = self.unit.symbol
        if unit_symbol == "dimensionless":
            unit_symbol = ""
        
        s = f"{str(self.value)} {unit_symbol}" 
        return s
    
    
def unece_unit_code_from_quantity(q:Quantity):
        by_name =   [ u['commonCode'] for u in unece_units() if u.get('name','') == q.unit.name] 
        by_symbol = [ u['commonCode'] for u in unece_units() if u.get('symbol','') == q.unit.symbol]
        code = list(set(by_name) | set(by_symbol))
        if len(code) != 1:
            raise ValueError(f'No UNECE unit code found for Quantity {str(q)}' ) 
        return code[0]
    
    
# class DataTable(list):
#     def __init__(self, headers:tuple[str, Any]):
#         for h in headers:
#             if len(h) != 2:
#                 raise ValueError(f'Headers must be tuples of length two. With a column name and type.')
#             if not isinstance(h[0], str):
#                 raise ValueError(f'Invalid type of header name {h[0]}. Must be str')
#             if not (h[1]):
#                 raise ValueError(f'Header type cannot be None')
#         self.headers = headers
#         super().__init__()
    
#     def append(self, row:list):
#         if len(row) != len(self.headers):
#             raise ValueError(f'Row has different length than headers')
#         super().append(row)

class DataTable(list):
    def __init__(self, col_names:list[str]=None):
        self.col_names = col_names
        self.row_template = None
        super().__init__()
    
    def append(self, row:list):
        if not self.row_template:
            self.row_template = row.copy()
        super().append(row)
        
    def extend(self, iterable):
        for item in iterable:
            self.append(item) 
        
        

         
if __name__ == "__main__":
    pass                
        
        

    
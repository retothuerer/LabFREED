

from datetime import date, datetime, time
from typing import Union
from pydantic import BaseModel, Field, PrivateAttr, model_validator

from labfreed.utilities.base36 import base36
from labfreed.trex.python_convenience.quantity import Quantity


class DataTable(BaseModel):
    _row_template:list[str, Quantity | datetime | time | date | bool | str | base36] =  PrivateAttr(default_factory=list)
    col_names: list[str] = Field(default_factory=list)
    data:list[list[Union[Quantity, datetime, time, date, bool, str, base36, None]]] = Field(default_factory=list)
    
    @property
    def row_template(self):
        return self._row_template
    
    @model_validator(mode='after')
    def get_row_template(self):
        for r in self.data:
            if all([e is not None for e in r]):
                self._row_template = r.copy()
            break
        if not self._row_template:
            raise ValueError('All columns contained at least one None. This is invalid')
        return self
        
       
    def append(self, row:list):
        if not isinstance(row, list):
            raise ValueError('row must be a list of values')
        if not self._row_template:
            self._row_template = row.copy()
        if not len(row) == len(self._row_template):
            raise ValueError('row is not of same length as the row template.')
        if not self.col_names:
            self.col_names = [f"Col{i}" for i in range(len(self._row_template))]
        
        # make sure int and float have a unit, if the row_tempalet has one
        for i, e in enumerate(row):
            if isinstance(e, float|int) and isinstance(self._row_template[i], Quantity):
                unit = self._row_template[i].unit
                row[i] = Quantity(value=e, unit=unit)     
        self.data.append(row)
        
        
    def extend(self, iterable):
        for item in iterable:
            if not len(item) == len(self._row_template):
                raise ValueError('row is not of same length as the row template.')
            self.data.append(item) 
            
    def get_column(self, col:str|int) -> list:
        if isinstance(col, str):
            col_index = self.col_names.index()
        else:
            col_index = col
        col_data = [row[col_index] for row in self.data]
        return col_data
    
    def get_row(self, row_index:int) -> list:
        return self.data[row_index]
    
    def get_cell(self, row_index:int, col:str|int):
        if isinstance(col, str):
            col_index = self.col_names.index()
        else:
            col_index = col
        return self.data[row_index][col_index]
        

    
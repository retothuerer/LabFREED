from __future__ import annotations  # optional in 3.11, but recommended for consistency

from abc import ABC
from typing import Self
from pydantic import Field, computed_field, model_validator

from rich import print
from rich.text import Text
from rich.table import Table

from labfreed.labfreed_infrastructure import ValidationMsgLevel

from labfreed.pac_cat.category_base import Category
from labfreed.pac_cat.predefined_categories import Data_Calibration, Data_Method, Data_Progress, Data_Result, Material_Consumable, Material_Device, Material_Misc, Material_Substance, Data_Static
from labfreed.pac_id import PACID, IDSegment

''' Configure pdoc'''

    
class PAC_CAT(PACID):
    ''' 
    Extends a PAC-ID with interpretation of the identifier as categories
    '''
    categories:list[Category] = Field(default_factory=list)
    '''The categories present in the PAC-ID's identifier'''
    
    @property
    def identifier(self) -> list[IDSegment]:
        out = list()
        for category in self.categories:
            out.append(IDSegment(value=category.key))
            out.extend(category.segments)
        return out
    
    def serialize(self, use_short_notation=True):
        id_segments = ''
        for c in self.categories:
            segments = c.segments(use_short_notation=use_short_notation)
            for s in segments:
                s:IDSegment = s
                if s.key:
                    id_segments += f'/{s.key}:{s.value}'
                else:
                    id_segments += f'/{s.value}'
    
        out = f"HTTPS://PAC.{self.issuer}{id_segments}"
        return out
    

    
    
    def get_category(self, key) -> Category:
        """Helper to get a category by key
        """
        
        tmp = [c for c in self.categories if c.key == key]
        if not tmp:
            return None
        return tmp[0]
    
    
    @classmethod
    def from_pac_id(cls, pac_id:PACID) -> Self:
        '''Constructs a PAC-CAT from a PAC-ID'''
        issuer = pac_id.issuer
        
        category_segments = cls._split_segments_by_category(pac_id.identifier)
        categories = list()
        for c in category_segments:
            categories.append(cls._cat_from_cat_segments(c))
        
        return PAC_CAT(issuer=issuer, categories=categories, identifier=pac_id.identifier)
        
            
    @classmethod
    def _cat_from_cat_segments(cls, segments:list[IDSegment]) -> Category:
        segments = segments.copy()
        category_key = segments[0].value         
        segments.pop(0)
        
        mapping  = {
                '-MD': Material_Device,
                '-MS': Material_Substance,
                '-MC': Material_Consumable,
                '-MM': Material_Misc,
                '-DM': Data_Method,
                '-DR': Data_Result,
                '-DC': Data_Calibration,
                '-DP': Data_Progress,
                '-DS': Data_Static 
        }
        known_cat = mapping.get(category_key)
        
        if not known_cat:
            return Category(key=category_key, segments=segments)

        # implicit segment keys
        model_dict = {v.alias: None for k, v in known_cat.model_fields.items() if v.alias and k not in ['key','additional_segments']}
        for k, seg in zip(model_dict.keys(), segments.copy()):
            if seg.key:
                break
            model_dict[k] = seg.value
            segments.pop(0)
            
        # try to fill model keys if not already set
        for s in segments:
            if s.key in model_dict and not model_dict.get(s.key):
                model_dict[s.key] = s.value
                segments.remove(s)
            
        model_dict['additional_segments'] = segments
        model_dict['key'] = category_key
        return known_cat(**model_dict)
    
    @staticmethod
    def _split_segments_by_category(segments:list[IDSegment]) -> list[list[IDSegment]]:
        category_segments = list()
        c = list()
        for s in segments:
            # new category starts with "-"
            if s.value[0] == '-':
                cat_key = s.value
                c = [s]
                category_segments.append(c)
            else:
                c.append(s)
                
        # first cat can be empty > remove
        category_segments = [c for c in category_segments if len(c) > 0]
                            
        return category_segments
    
    
    @model_validator(mode='after')
    def _check_keys_are_unique_in_each_category(self) -> Self:
        for c in self.categories:
            keys = [s.key for s in c.segments if s.key]
            duplicate_keys = [k for k in set(keys) if keys.count(k) > 1]
            if duplicate_keys:
                for k in duplicate_keys:
                    self._add_validation_message(
                        source=f"identifier {k}",
                        level = ValidationMsgLevel.ERROR,
                        msg=f"Duplicate key {k} in category {c.key}",
                        highlight_pattern = k
                    )
            return self
        
    def print_categories(self):
        table = Table(title=f'Categories in {str(self)}', show_header=False)
        table.add_column('0')
        table.add_column('1')
        s = ''
        for i, c in enumerate(self.categories):
            if i == 0:
                title = Text('Main Category', style='bold')
            else:
                title = Text('Category', style='bold')
            
            table.add_row(title)
            
            for field_name, field_info in c.model_fields.items():
                if not getattr(c, field_name):
                    continue
                table.add_row(f"{field_name} ({field_info.alias or ''})",
                              f" {getattr(c, field_name)}"
                              )      
            table.add_section()        
        print(table)
        

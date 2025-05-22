from __future__ import annotations  # optional in 3.11, but recommended for consistency

from typing import Self
from pydantic import computed_field, model_validator

from rich import print
from rich.text import Text
from rich.table import Table

from labfreed.labfreed_infrastructure import ValidationMsgLevel

from labfreed.pac_cat.category_base import Category
from labfreed.pac_cat.predefined_categories import category_key_to_class_map
from labfreed.pac_id.id_segment import IDSegment
from labfreed.pac_id.pac_id import PAC_ID

''' Configure pdoc'''

    
class PAC_CAT(PAC_ID):
    ''' 
    Extends a PAC-ID with interpretation of the identifier as categories
    '''
    @computed_field
    @property
    def categories(self) -> list[Category]: 
        '''The categories present in the PAC-ID's identifier'''
        category_segments = self._split_segments_by_category(self.identifier)
        categories = list()
        for c in category_segments:
            categories.append(self._cat_from_cat_segments(c))
        return categories
    
    

    def get_category(self, key) -> Category:
        """Helper to get a category by key
        """ 
        tmp = [c for c in self.categories if c.key == key]
        if not tmp:
            return None
        return tmp[0]
    
    
    @classmethod
    def from_categories(cls, issuer:str, categories:list[Category]) -> PAC_CAT:
        identifier = list()
        for category in categories:
            identifier.append(IDSegment(value=category.key))
            identifier.extend(category.segments)
        return PAC_CAT(issuer=issuer, identifier=identifier)
    
    
    @classmethod
    def from_pac_id(cls, pac_id:PAC_ID) -> Self:
        '''Constructs a PAC-CAT from a PAC-ID'''
        return PAC_CAT(issuer=pac_id.issuer, identifier=pac_id.identifier)
    

    
    def to_pac_id(self) -> PAC_ID:
        return PAC_ID(issuer=self.issuer, identifier=self.identifier)
        
            
    @classmethod
    def _cat_from_cat_segments(cls, segments:list[IDSegment]) -> Category:
        segments = segments.copy()
        category_key = segments[0].value         
        segments.pop(0)
        
        known_cat = category_key_to_class_map.get(category_key)
        
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
        for s in segments.copy():
            if s.key in model_dict.keys() and not model_dict.get(s.key):
                model_dict[s.key] = s.value
                segments.remove(s)
            
        model_dict['additional_segments'] = segments
        model_dict['key'] = category_key
        cat= known_cat(**model_dict)
        return cat
    
    @staticmethod
    def _split_segments_by_category(segments:list[IDSegment]) -> list[list[IDSegment]]:
        category_segments = list()
        c = list()
        for s in segments:
            # new category starts with "-"
            if s.value[0] == '-':
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
        
        
    @model_validator(mode='after')
    def _check_identifier_segment_keys_are_unique(self) -> Self:
        ''' override the validator of PAC-ID: in PAC-CAT segments can replicate in different categories'''
        return self
    
        
    def print_categories(self):
        table = Table(title=f'Categories in {str(self)}', show_header=False)
        table.add_column('0')
        table.add_column('1')
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
        

        

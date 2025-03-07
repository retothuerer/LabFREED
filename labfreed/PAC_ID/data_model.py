from typing import Optional
from typing_extensions import Self
from pydantic import BaseModel, Field, computed_field, conlist, model_validator
from abc import ABC, abstractproperty, abstractstaticmethod

class IDSegment(BaseModel):
    key:Optional[str] = Field(None, pattern=r'^[A-Z0-9-+]+$', min_length=1)
    value:str = Field(..., pattern=r'^[A-Z0-9-+]+$', min_length=1)


class Category(BaseModel):
    key:str|None = None
    segments: list[IDSegment]


class Identifier(BaseModel):
    segments: conlist(IDSegment, min_length=1) = Field(..., exclude=True) # exclude=True prevents this from being serialized by Pydantic
        
    @computed_field
    @property
    def categories(self) -> list[Category]:
        categories = list()
        c = Category(segments=[])
        categories.append(c)
        for s in self.segments:
            # new category starts with "-"
            if s.value[0] == '-':
                cat_key = s.value
                c = Category(key=cat_key, segments=[])
                categories.append(c)
            else:
                c.segments.append(s)
            
        # the first category might have no segments. remove categories without segments
        if not categories[0].segments:
            categories = categories[1:]
                
        return categories
    
    @model_validator(mode='after')
    def check_keys_are_unique_in_each_category(self) -> Self:
        for c in self.categories:
            keys = [s.key for s in c.segments if s.key]
            duplicate_keys = [k for k in set(keys) if keys.count(k) > 1]
            if duplicate_keys:
                raise ValueError(f'Duplicate keys {",".join(duplicate_keys)} in category {c.key}')
            return self
       
    @staticmethod 
    def from_categories(categories:list[Category]) :
        segments = list()
        for c in categories:
            if c.key:
                segments.append(IDSegment(value=c.key))
            segments.extend(c.segments)
        return Identifier(segments=segments)
        
    

class Extension(ABC, BaseModel): 
    
    @abstractproperty
    def name(self)->str:
        pass
    
    @abstractproperty
    def type(self)->str:
        pass
    
    @abstractproperty
    def data(self)->str:
        pass
    
    @abstractstaticmethod
    def from_spec_fields(name, type, data):
        pass
    
    
class UnknownExtension(Extension):
    name_:str
    type_:str
    data_:str
    
    @property
    def name(self)->str:
        return self.name_
    
    @property
    def type(self)->str:
        return self.type_
    
    @property
    def data(self)->str:
        return self.data_
       
    @staticmethod
    def from_spec_fields(name, type, data):
        return UnknownExtension(name_=name, type_=type, data_=data)
    


class PACID(BaseModel):
    issuer:str
    identifier: Identifier
    
    
class PACID_With_Extensions(BaseModel):
    pac_id: PACID
    extensions: list[Extension] = Field(default_factory=list)






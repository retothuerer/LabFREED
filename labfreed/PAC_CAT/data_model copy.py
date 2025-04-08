# import re
# from typing import Optional
# from typing_extensions import Self
# from pydantic import Field, ValidationInfo, computed_field, conlist, model_validator, field_validator

# from abc import ABC, abstractproperty, abstractstaticmethod

# from labfreed.PAC_ID.data_model import PACID

# from ..utilities.well_known_keys import WellKnownKeys
# from labfreed.validation import BaseModelWithValidationMessages, ValidationMessage, hsegment_pattern, domain_name_pattern


# # class IDSegment(BaseModelWithValidationMessages):
# #     key:str|None = None
# #     value:str  
    
# #     @model_validator(mode="after")
# #     def validate_segment(self):
# #         key = self.key or ""
# #         value = self.value 
        
# #         # MUST be a valid hsegment according to RFC 1738, but without * (see PAC-ID Extension)
# #         # This means it must be true for both, key and value
# #         if not_allowed_chars := set(re.sub(hsegment_pattern, '', key)):
# #             self.add_validation_message(
# #                     source=f"id segment key {key}",
# #                     type="Error",
# #                     msg=f"{' '.join(not_allowed_chars)} must not be used.",
# #                     recommendation = "The segment key must be a valid hsegment",
# #                     highlight_pattern = key,
# #                     highlight_sub = not_allowed_chars
# #             )
        
# #         if not_allowed_chars := set(re.sub(hsegment_pattern, '', value)):
# #             self.add_validation_message(
# #                     source=f"id segment key {value}",
# #                     type="Error",
# #                     msg=f"{' '.join(not_allowed_chars)} must not be used.",
# #                     recommendation = "The segment key must be a valid hsegment",
# #                     highlight_pattern = value,
# #                     highlight_sub = not_allowed_chars
# #             )

# #         # Segment key SHOULD be limited to A-Z, 0-9, and -+..
# #         if not_recommended_chars := set(re.sub(r'[A-Z0-9-:+]', '', key)):
# #             self.add_validation_message(
# #                     source=f"id segment key {key}",
# #                     type="Recommendation",
# #                     msg=f"{' '.join(not_recommended_chars)} should not be used.",
# #                     recommendation = "SHOULD be limited to A-Z, 0-9, and -+",
# #                     highlight_pattern = key,
# #                     highlight_sub = not_recommended_chars
# #                 )
            
# #         # Segment key should be in Well know keys
# #         if key and key not in [k.value for k in WellKnownKeys]:
# #             self.add_validation_message(
# #                     source=f"id segment key {key}",
# #                     type="Recommendation",
# #                     msg=f"{key} is not a well known segment key.",
# #                     recommendation = "RECOMMENDED to be a well-known id segment key.",
# #                     highlight_pattern = key
# #                 )
            
            
# #         # Segment value SHOULD be limited to A-Z, 0-9, and -+..
# #         if not_recommended_chars := set(re.sub(r'[A-Z0-9-:+]', '', value)):
# #             self.add_validation_message(
# #                     source=f"id segment value {value}",
# #                     type="Recommendation",
# #                     msg=f"Characters {' '.join(not_recommended_chars)} should not be used.",
# #                     recommendation = "SHOULD be limited to A-Z, 0-9, and -+",
# #                     highlight_pattern = value,
# #                     highlight_sub = not_recommended_chars
# #                 )
            
# #         # Segment value SHOULD be limited to A-Z, 0-9, and :-+ for new designs.
# #         # this means that ":" in key or value is problematic
# #         if ':' in key:
# #             self.add_validation_message(
# #                     source=f"id segment key {key}",
# #                     type="Recommendation",
# #                     msg=f"Character ':' should not be used in segment key, since this character is used to separate key and value this can lead to undefined behaviour.",
# #                     highlight_pattern = key
# #                 )
# #         if ':' in value:
# #             self.add_validation_message(
# #                     source=f"id segment value {value}",
# #                     type="Recommendation",
# #                     msg=f"Character ':' should not be used in segment value, since this character is used to separate key and value this can lead to undefined behaviour.",
# #                     highlight_pattern = value
# #                 )
                
# #         return self
     
  
    




# class PAC_CAT(PACID):
        
#     @computed_field
#     @property
#     def categories(self) -> list[Category]:
#         categories = list()
#         c = Category(segments=[])
#         categories.append(c)
#         for s in self.segments:
#             # new category starts with "-"
#             if s.value[0] == '-':
#                 cat_key = s.value
#                 c = Category(key=cat_key, segments=[])
#                 categories.append(c)
#             else:
#                 c.segments.append(s)
            
#         # the first category might have no segments. remove categories without segments
#         if not categories[0].segments:
#             categories = categories[1:]
                
#         return categories
    
#     @model_validator(mode='after')
#     def check_keys_are_unique_in_each_category(self) -> Self:
#         for c in self.categories:
#             keys = [s.key for s in c.segments if s.key]
#             duplicate_keys = [k for k in set(keys) if keys.count(k) > 1]
#             if duplicate_keys:
#                 for k in duplicate_keys:
#                     self.add_validation_message(
#                         source=f"identifier {k}",
#                         type="Error",
#                         msg=f"Duplicate key {k} in category {c.key}",
#                         highlight_pattern = k
#                     )
#             return self
        
#     # @model_validator(mode='after')
#     # def check_length(self) -> Self:
#     #     l = 0
#     #     for s in self.segments:
#     #         if s.key:
#     #             l += len(s.key)
#     #             l += 1 # for ":"
#     #         l += len(s.value)
#     #     l += len(self.segments) - 1 # account for "/" separating the segments
        
#     #     if l > 256:
#     #         self.add_validation_message(
#     #                     source=f"identifier",
#     #                     type="Error",
#     #                     msg=f'Identifier is {l} characters long, Identifier must not exceed 256 characters.',
#     #                     highlight_pattern = ""
#     #                 )
#     #     return self
       
#     @staticmethod 
#     def from_categories(categories:list[Category]) :
#         segments = list()
#         for c in categories:
#             if c.key:
#                 segments.append(IDSegment(value=c.key))
#             segments.extend(c.segments)
#         return Identifier(segments=segments)
        
    



# # class PACID(BaseModelWithValidationMessages):
# #     issuer:str
# #     identifier: Identifier
    
# #     @model_validator(mode="after")
# #     def validate_issuer(self):
# #         if not re.fullmatch(domain_name_pattern, self.issuer):
# #             self.add_validation_message(
# #                     source="PAC-ID",
# #                     type="Error",
# #                     highlight_pattern=self.issuer,
# #                     msg=f"Issuer must be a valid domain name. "
# #                 )
         
# #         # recommendation that A-Z, 0-9, -, and . should be used
# #         if not_recommended_chars := set(re.sub(r'[A-Z0-9\.-]', '', self.issuer)):
# #             self.add_validation_message(
# #                     source="PAC-ID",
# #                     type="Recommendation",
# #                     highlight_pattern=self.issuer,
# #                     highlight_sub=not_recommended_chars,
# #                     msg=f"Characters {' '.join(not_recommended_chars)} should not be used. Issuer SHOULD contain only the characters A-Z, 0-9, -, and . "
# #                 )
# #         return self
    
# #     def __str__(self):
# #         id_segments = ''
# #         for s in self.identifier.segments:
# #             if s.key:
# #                 id_segments += f'/{s.key}:{s.value}'
# #             else:
# #                 id_segments += f'/{s.value}'
    
# #         out = f"HTTPS://PAC.{self.issuer}{id_segments}"
# #         return out
    
    
    
    
# # class PACID_With_Extensions(BaseModelWithValidationMessages):
# #     pac_id: PACID
# #     extensions: list[Extension] = Field(default_factory=list)
    
# #     def __str__(self):
# #         out = str(self.pac_id)
# #         out += '*'.join(str(e) for e in self.extensions)
        
# #     def get_extension_of_type(self, type:str) -> list[Extension]:
# #         return [e for e in self.extensions if e.type == type]
    
# #     def get_extension(self, name:str) -> Extension|None:
# #         out = [e for e in self.extensions if e.name == name]
# #         if not out:
# #             return None
# #         return out[0]
        





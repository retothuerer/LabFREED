from functools import cached_property
from pathlib import Path
from urllib.parse import urlparse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field
from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup, Attributes, Reference, Resource
from labfreed.pac_attributes.well_known_attribute_keys import MetaAttributeKeys
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_cat.predefined_categories import PredefinedCategory
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.services import ServiceGroup, Service
from labfreed.labfreed_extended.app.formatted_print import StringIOLineBreak
from labfreed.trex.facade.data_table import DataTable
from labfreed.trex.facade.t_rex import T_REX
from labfreed.well_known_extensions.display_name_extension import DisplayNameExtension
from enum import Enum

class PacInfo(BaseModel):
    """A convenient collection of information about a PAC-ID"""
    pac_id:PAC_ID

    user_handovers: list[ServiceGroup] = Field(default_factory=list)
    actions: list[ServiceGroup] = Field(default_factory=list)
    attribute_groups:dict[str, AttributeGroup] = Field(default_factory=dict)
    
    
    # info about pac-id
    
    @cached_property
    def is_item_serialized(self) -> bool|None: #indicates if the item is at product level (e.g. BAL500), as opposed to a serialized instance thereof (e.g. BAL500 with SN 1234)
        if not isinstance(self.pac_id, PAC_CAT):
            return None
        cat = self.main_category
        if not isinstance(cat, PredefinedCategory):
            return None
        
        return cat.is_serialized

    
    @cached_property
    def pac_url(self):
        return self.pac_id.to_url(include_extensions=False)
    
    @cached_property
    def main_category(self):
        if isinstance(self.pac_id, PAC_CAT):
            return self.pac_id.categories[0]
        else:
            return None
        
        
    
    # attached data
        
    @cached_property
    def attached_data(self) -> dict[str, T_REX]:
        return { trex_ext.name: T_REX.from_trex(trex=trex_ext.trex) for trex_ext in self.pac_id.get_extension_of_type('TREX')}


    @cached_property
    def summary(self) -> T_REX:
        return T_REX.from_trex(self.pac_id.get_extension('SUM').trex)


    @cached_property
    def status(self) -> T_REX:
        return T_REX.from_trex(self.pac_id.get_extension('STATUS').trex)

        
        
        
    # Handovers and Actions
        
    def get_user_handovers_by_intent(self, intent:str, partial_match=False) -> list[Service]:
        # capture the common mistake of forgetting to access key of enum
        if isinstance(intent, Enum):
            intent = intent.value    
        services = [s for sg in self.user_handovers for s in sg.services if self._match_intent(intent, s.application_intents, partial_match)]
        return services
    
    def get_user_handover_by_intent(self, intent:str, partial_match=False, mode="first"):
        if isinstance(intent, Enum):
            intent = intent.value 
        handovers = self.get_user_handovers_by_intent(intent=intent, partial_match=partial_match)
        return self._pick_from_list(handovers, mode)
        
    
    
    def get_actions_by_intent(self, intent:str, partial_match=False) -> list[Service]:
        if isinstance(intent, Enum):
            intent = intent.value 
        actions = [s for sg in self.actions for s in sg.services if self._match_intent(intent, s.application_intents, partial_match)]
        return actions
    
    def get_action_by_intent(self, intent:str, partial_match=False, mode="first"):
        if isinstance(intent, Enum):
            intent = intent.value 
        actions = self.get_actions_by_intent(intent=intent, partial_match=partial_match)
        return self._pick_from_list(actions, mode)
    
    
    def _match_intent(self, intent, intents, partial_match):
            if partial_match:
                # intent 'document' should match 'document-operation-manual' etc
                return any([intent in i for i in intents])
            else:
                # only exact match
                return intent in intents


    # key identifies *what a service is* via a shared, IRI-anchored vocabulary term
    # (e.g. "this is a Material Safety Data Sheet") - the same "key" concept PAC-ID
    # Attributes already uses (see get_attribute/get_attributes below) - unlike
    # application_intents (a short, free-text string identifying *which use case*
    # picks it). Exact match only, since IRIs aren't meant to be fuzzy-matched the way
    # dash-separated intents are (see get_user_handovers_by_intent's partial_match).

    def get_user_handovers_by_key(self, key:str) -> list[Service]:
        if isinstance(key, Enum):
            key = key.value
        return [s for sg in self.user_handovers for s in sg.services if s.key == key]

    def get_user_handover_by_key(self, key:str, mode="first"):
        if isinstance(key, Enum):
            key = key.value
        handovers = self.get_user_handovers_by_key(key)
        return self._pick_from_list(handovers, mode)

    def get_actions_by_key(self, key:str) -> list[Service]:
        if isinstance(key, Enum):
            key = key.value
        return [s for sg in self.actions for s in sg.services if s.key == key]

    def get_action_by_key(self, key:str, mode="first"):
        if isinstance(key, Enum):
            key = key.value
        actions = self.get_actions_by_key(key)
        return self._pick_from_list(actions, mode)


    @cached_property
    def important_handovers(self) -> list[Service]:
        return self.get_user_handovers_by_intent('important')
    
    
    @cached_property
    def important_actions(self) -> list[Service]:
        return self.get_actions_by_intent('important')
        
        
        
        
        
        
     # Attributes   
        
    @cached_property
    def _all_attributes(self) -> dict[str, Attribute]:
        out = {}
        for ag in self.attribute_groups.values():
            out.update(ag.attributes)   
        return out
    
        
    def get_attributes(self, key:str) -> list[Attribute]:
        # capture the common mistake of forgetting to access key of enum
        if isinstance(key, Enum):
            key = key.value    
        attributes = [a for k, a in self._all_attributes.items() if key in a.key]
        return attributes  
    
    def get_attribute(self, key:str, mode="first"):  
        # capture the common mistake of forgetting to access key of enum
        if isinstance(key, Enum):
            key = key.value      
        attributes = self.get_attributes(key)
        return self._pick_from_list(attributes, mode)

        
    def _pick_from_list(self, list, mode):
        if mode not in ['first', 'last']:
            raise ValueError('mode must be "first or "last" ')
        
        if not list:
            return None
        if mode == 'first':
            return list[0]
        if mode == 'last':
            return list[-1]
        
        
    @cached_property
    def image_url(self) -> str|None:
        image_attr = self._all_attributes.get(MetaAttributeKeys.IMAGE)
        if not image_attr:
            return None
        if isinstance(image_attr.values, Resource):
            return image_attr.values.root
        if isinstance(image_attr.values, str):
            return image_attr.values
        
        
    @cached_property
    def display_name(self) -> str|None:
        display_name = None
        pac = self.pac_id
        if dn := pac.get_extension('N'):
            dn = DisplayNameExtension.from_extension(dn)
            display_name = dn.display_name or ""
        # there can be a display name in attributes, too

        if dn_attr := self._all_attributes.get(MetaAttributeKeys.DISPLAYNAME): 
            dn = dn_attr.values
            display_name = dn + f' ( aka {display_name} )' if display_name else dn
            
        if not display_name and self.main_category:
            seg_240 = [s for s in self.main_category.segments if s.key=="240"]
            if seg_240:
                display_name = seg_240[0].value
            
        return display_name
    
    
    @cached_property
    def safety_pictograms(self) -> dict[str, Attribute]:
        pictogram_attributes = {k: a for k, a in self._all_attributes.items() if "https://labfreed.org/ghs/pictogram/" in a.key}
        return pictogram_attributes    
    
    
    @cached_property
    def qualification_state(self) -> Attribute:
        if state := self._all_attributes.get("https://labfreed.org/qualification/status"): 
            return state

    
         


        
    
    
    
    
    
    
    
    
########
    
    
    def format_for_print(self, markup:str='rich') -> str:
        
        printout = StringIOLineBreak(markup=markup)
        
        printout.write(f"for {self.pac_url}")
        
        printout.title1("Info")
        printout.key_value("Display Name", self.display_name)
        
        if isinstance(self.pac_id, PAC_CAT):
            printout.title1("Categories")
            for c in self.pac_id.categories:
                category_name = c.__class__.__name__
                printout.title2(category_name)
                for k,v in c.segments_as_dict().items():
                    printout.key_value(k, v)
                
                    
        printout.title1("Services")
        for sg in self.user_handovers:           
            printout.title2(f"(from {sg.origin})")
            for s in sg.services:
                printout.link(s.service_name, s.url)          
        
        
        printout.title1("Attributes")
        for ag in self.attribute_groups.values():  
            printout.title2(f'{ag.group_label} (from {ag.origin})')
            for v in ag.attributes.values():
                v:Attribute
                #print(f'{k}: ({v.label})           :: {v.value}  ')
                printout.key_value(v.label, ', '.join([str(e) for e in v.value_list]))
      
        out =  printout.getvalue()

        return out
    
    
    

    
    
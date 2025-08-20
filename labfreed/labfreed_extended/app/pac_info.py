

from functools import cached_property
from pydantic import BaseModel, Field
from labfreed.pac_attributes.pythonic.py_attributes import pyAttribute, pyAttributeGroup, pyAttributes
from labfreed.pac_attributes.well_knonw_attribute_keys import MetaAttributeKeys
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.services import ServiceGroup
from labfreed.labfreed_extended.app.formatted_print import StringIOLineBreak
from labfreed.trex.pythonic.pyTREX import pyTREX
from labfreed.well_known_extensions.display_name_extension import DisplayNameExtension


class PacInfo(BaseModel):
    """A convenient collection of information about a PAC-ID"""
    pac_id:PAC_ID
    user_handovers: list[ServiceGroup] = Field(default_factory=list)
    attributes:dict[str, pyAttributeGroup] = Field(default_factory=dict)
    
    @property
    def pac_url(self):
        return self.pac_id.to_url(include_extensions=False)
    
    @property
    def main_category(self):
        if isinstance(self.pac_id, PAC_CAT):
            return self.pac_id.categories[0]
        else:
            return None
        
    @property
    def attached_data(self):
        return { trex_ext.name: pyTREX.from_trex(trex=trex_ext.trex) for trex_ext in self.pac_id.get_extension_of_type('TREX')}

    
    @property
    def summary(self):
        return self.pac_id.get_extension('SUM')
    
    @property
    def image_url(self) -> str:
        if meta := self.attributes.get(MetaAttributeKeys.GROUPKEY.value):
            image_attr = meta.attributes.get(MetaAttributeKeys.IMAGE.value)
            return image_attr.value
        
        
    @property
    def display_name(self) -> str|None:
        display_name = None
        pac = self.pac_id
        if dn := pac.get_extension('N'):
            dn = DisplayNameExtension.from_extension(dn)
            display_name = dn.display_name or ""
        # there can be a display name in attributes, too

        if dn_attr := self._all_attributes.get(MetaAttributeKeys.DISPLAYNAME.value): 
            dn = dn_attr.value
            display_name = dn + f' ( aka {display_name} )' if display_name else dn
        return display_name
    
    
    @property
    def safety_pictograms(self) -> dict[str, pyAttribute]:
        pictogram_attributes = {k: a for k, a in self._all_attributes.items() if "https://labfreed.org/ghs/pictogram/" in a.key}
        return pictogram_attributes    
        
        
    @cached_property
    def _all_attributes(self) -> dict[str, pyAttribute]:
        out = {}
        for ag in self.attributes.values():
            out.update(ag.attributes)   
        return out
    
    
    
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
        for ag in self.attributes.values():  
            printout.title2(f'{ag.label} (from {ag.origin})')
            for v in ag.attributes.values():
                v:pyAttribute
                #print(f'{k}: ({v.label})           :: {v.value}  ')
                printout.key_value(v.label, v.value)
      
        out =  printout.getvalue()

        return out
    
        
        
        
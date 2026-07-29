from abc import ABC, abstractmethod, abstractproperty
from labfreed.labfreed_infrastructure import LabFREED_ValidationError
from labfreed.pac_attributes.api_data_models.response import Attribute, AttributeGroup
from labfreed.pac_cat.pac_cat import PAC_CAT


class AttributeGroupDataSource(ABC):
    
    def __init__(self, attribute_group_key:str, include_extensions:bool=False, is_static:bool=False, ):
        self._attribute_group_key = attribute_group_key
        self._include_extensions = include_extensions
        self._is_static = is_static
       
    @property
    def is_static(self) -> bool:
        return self._is_static
    
    
    @property
    def attribute_group_key(self):
        return self._attribute_group_key
    
    @abstractproperty
    def provides_attributes(self):
        pass
    
    @abstractmethod
    def attributes(self, pac_url: str) -> AttributeGroup:
        pass
    

class Dict_DataSource(AttributeGroupDataSource):
    def __init__(self, data:dict[str, dict[str, Attribute]], uses_pac_cat_short_form=True, pac_to_key: callable = None, *args, **kwargs):
        if not all([isinstance(e, dict) for e in data.values()]):
            raise ValueError('Invalid data')
        
        self._data = data
        self.uses_pac_cat_short_form = uses_pac_cat_short_form
        self._pac_to_key = pac_to_key
        
        super().__init__(*args, **kwargs)       
        
    
    @property
    def provides_attributes(self):
        return list(set([a.key for attributes in self._data.values() for a in attributes.values()]))
    
           
    def attributes(self, pac_url: str) -> AttributeGroup:
        canonical_url = pac_url
        try:
            # suppress_validation_errors=True: pac_url only has to be an IRI here, not a
            # strictly valid PAC-ID (e.g. a trailing-slash id, or a generic non-PAC-ID
            # IRI) - falling back to the raw input below is the expected, routine case,
            # not something worth logging as an error.
            p = PAC_CAT.from_url(pac_url, suppress_validation_errors=True)
            if p.is_valid:
                canonical_url = p.to_url(use_short_notation=self.uses_pac_cat_short_form, include_extensions=self._include_extensions)
        except LabFREED_ValidationError:
            ... # might as well try to match the original input

        # canonicalization can drop information the stored data is still keyed by (e.g. a
        # tolerated trailing '/' - see design-choices.md "Empty id segments"), so fall back
        # to the raw, as-given input if the canonical form doesn't find a match.
        attributes = self._data.get(self._pac_to_key(canonical_url) if self._pac_to_key else canonical_url)
        if attributes is None and canonical_url != pac_url:
            attributes = self._data.get(self._pac_to_key(pac_url) if self._pac_to_key else pac_url)
        if not attributes:
            if 'default' in self._data.keys():
                attributes = self._data.get('default', None)
            else:
                return None

        return AttributeGroup(group_key=self._attribute_group_key,
                              attributes=attributes)
        
        
        

    
    

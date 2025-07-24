from abc import ABC, abstractmethod, abstractproperty
from datetime import datetime, timezone

from labfreed.pac_attributes.api_data_models.request import AttributeRequestPayload
from labfreed.pac_attributes.api_data_models.response import  AttributeGroup, AttributeResponsePayload,  AttributesOfPACID, ReferenceAttribute
from labfreed.pac_attributes.server.attribute_data_sources import AttributeGroupDataSource
from labfreed.pac_attributes.server.translation_data_sources import OnthologyTranslationDataSource
from translations import TranslationsForOntology, Term, Translation
from labfreed.pac_id.pac_id import PAC_ID




       
    

    


class InvalidRequestError(ValueError):
    pass


    
class AttributeServerRequestHandler():
    def __init__(self, data_sources:list[AttributeGroupDataSource], translation_data_sources:list[OnthologyTranslationDataSource]):
        if isinstance(data_sources, AttributeGroupDataSource):
            data_sources = [data_sources]
        self._attribute_group_data_sources: list[AttributeGroupDataSource] = data_sources
        
        self._translation_data_sources: list[OnthologyTranslationDataSource] = {tds.onthology: tds for tds in translation_data_sources}
               
        
    def handle_attribute_request(self, json_request_body:str) -> str:
        try:
            r = AttributeRequestPayload.model_validate_json(json_request_body)
        except:
            raise InvalidRequestError
        response_timestamp = datetime.now(tz=timezone.utc) # UTC !!
        attributes_for_pac_id = []
        referenced_pac_ids = []
        for pac_url in r.pac_urls:
            attributes_for_pac = self.get_attributes_for_pac_id(pac_url=pac_url, 
                                                                response_timestamp=response_timestamp, 
                                                                restrict_to_attribute_groups = r.restrict_to_attribute_groups)
            attributes_for_pac_id.append(attributes_for_pac)
            ref = self.get_referenced_pac_ids(attributes_for_pac)
            if ref:
                referenced_pac_ids.extend(ref)
            
        # also find attributes of referenced pac-ids 
        if not r.suppress_forward_lookup:
            for pac_url in referenced_pac_ids:
                attributes_for_pac = self.get_attributes_for_pac_id(pac_url=pac_url, 
                                                                    response_timestamp=response_timestamp,
                                                                    restrict_to_attribute_groups = r.restrict_to_attribute_groups)
                attributes_for_pac_id.append(attributes_for_pac)
            
        # attach relevant display names (fro attribute groups and attributes)
        if not r.suppress_translations:
            translations_by_ontology = self.get_translations(attributes_for_pac_id)
        else:
            translations_by_ontology = None
            
        response = AttributeResponsePayload(pac_attributes=attributes_for_pac_id, 
                                               translations_by_ontology=translations_by_ontology
                    ).to_json()
        return response
    

    def get_attributes_for_pac_id(self, pac_url:str, response_timestamp:datetime, restrict_to_attribute_groups:list[str]|None=None ):
        attribute_groups = []
        if restrict_to_attribute_groups:
            relevant_data_sources = [ds for ds in self._attribute_group_data_sources if ds.attribute_group_key in restrict_to_attribute_groups]
        else:
            relevant_data_sources = self._attribute_group_data_sources
        for ds in relevant_data_sources:
            try: 
                ag = ds.attributes(pac_url)
                if ag:
                    attribute_groups.append(ag)
            except Exception as e:
                e.add_note(f'Attribute Source {ds.attribute_group_key} encountered an error')
                raise e
                        
        return AttributesOfPACID(pac_url=pac_url, # return the pac_url as given, i.e. with the extension if there was one
                                 response_from=response_timestamp, 
                                 attribute_groups=attribute_groups)
        
    

    def get_referenced_pac_ids(self, attributes_for_pac:AttributesOfPACID):
        referenced_pacs = []
        for ag in attributes_for_pac.attribute_groups:
            for a in ag.attributes :
                if isinstance(a, ReferenceAttribute):
                    try:
                        PAC_ID.from_url(a.value)
                        referenced_pacs.append(a.value)
                    except:
                        pass
        return referenced_pacs
            
    def get_translations(self, attributes_for_pac_id): 
        ontology_map = {}  # ontology name → list of TermTranslations

        for ag_for_pac in attributes_for_pac_id:
            for ag in ag_for_pac.attribute_groups:
                ag: AttributeGroup
                ontology_name = ag.ontology
                translation_data_source: OnthologyTranslationDataSource = self._translation_data_sources.get(ontology_name, {})

                attribute_keys = [a.key for a in ag.attributes]
                all_keys = set([ag.key] + attribute_keys)

                for k in all_keys:
                    t = translation_data_source.get_translations_for(k)
                    if t:
                        ontology_map.setdefault(ontology_name, []).append(t)

        translations_by_ontology = [ TranslationsForOntology(ontology=name, terms=terms) for name, terms in ontology_map.items()
                                    ]
        return translations_by_ontology
            
            







    
        
        
        
    

    
    
    
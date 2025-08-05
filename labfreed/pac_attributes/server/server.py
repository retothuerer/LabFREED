import traceback
import warnings

import rich

from labfreed.pac_attributes.api_data_models.request import AttributeRequestPayload
from labfreed.pac_attributes.api_data_models.response import AttributeResponsePayload,  AttributesOfPACID, ReferenceAttribute
from labfreed.pac_attributes.api_data_models.server_capabilities_response import ServerCapabilities
from labfreed.pac_attributes.server.attribute_data_sources import AttributeGroupDataSource
from labfreed.pac_attributes.server.translation_data_sources import TranslationDataSource
from labfreed.pac_id.pac_id import PAC_ID


class InvalidRequestError(ValueError):
    pass


    
class AttributeServerRequestHandler():
    def __init__(self, data_sources:list[AttributeGroupDataSource], translation_data_sources:list[TranslationDataSource], default_language:str):
        '''Initializes the AttributeServerRequestHandler.
        - does some validation on availability of translations. NOTE: if data_sources or translation_data_sources change, this validation might get outdated'''
        if isinstance(data_sources, AttributeGroupDataSource):
            data_sources = [data_sources]
        self._attribute_group_data_sources: list[AttributeGroupDataSource] = data_sources
        
        
        
        # find which languages the sources consistently know
        self._translation_data_sources: list[TranslationDataSource] = translation_data_sources
        supported_languages = set()
        for tds in self._translation_data_sources:
            supported_languages.update(tds.supported_languages)
        if not supported_languages:
            raise ValueError("translation_data_sources contain no common fully supported language")
        
        if default_language not in supported_languages:
            raise ValueError(f"fallback language {default_language} is not supported by all translation data sources.")
        self._supported_languages = supported_languages
        self._default_language = default_language
        
        # check there are translations for all provided attributes
        missing_translations = []
        provided_attributes = [attr for ds in self._attribute_group_data_sources for attr in ds.provides_attributes]
        for language in self._supported_languages:
            for attribute_key in provided_attributes:
                if not self._get_display_name_for_key(attribute_key, language):
                    missing_translations.append((attribute_key, language))
        if missing_translations:
            rich.print('[yellow bold]WARNING: Missing translations[/yellow bold]')
            for mt in missing_translations:
                rich.print(f"[yellow]WARNING:[/yellow] '{mt[1]}' translation missing for '{mt[0]}'' ")
                    
               
        
    def handle_attribute_request(self, json_request_body:str) -> str:
        try:
            r = AttributeRequestPayload.model_validate_json(json_request_body)
        except Exception as e:
            raise InvalidRequestError
        attributes_for_pac_id = []
        referenced_pac_ids = set()
        for pac_url in r.pac_urls:
            attributes_for_pac = self._get_attributes_for_pac_id(pac_url=pac_url, 
                                                                restrict_to_attribute_groups = r.restrict_to_attribute_groups)
            attributes_for_pac_id.append(attributes_for_pac)
            ref = self._get_referenced_pac_ids(attributes_for_pac)
            if ref:
                referenced_pac_ids.update(ref)
            
        # also find attributes of referenced pac-ids 
        if not r.suppress_forward_lookup:
            for pac_url in referenced_pac_ids:
                attributes_for_pac = self._get_attributes_for_pac_id(pac_url=pac_url, 
                                                                    restrict_to_attribute_groups = r.restrict_to_attribute_groups)
                attributes_for_pac_id.append(attributes_for_pac)

        # add translations
        response_language = self._find_response_language(r.language_preferences)
        for e in attributes_for_pac_id:
            self._add_display_names(e, response_language)
            
        response = AttributeResponsePayload(pac_attributes=attributes_for_pac_id, language=response_language
                    ).to_json()
        return response
    



    def _get_attributes_for_pac_id(self, pac_url:str, restrict_to_attribute_groups:list[str]|None=None ) -> AttributesOfPACID:
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
                traceback.print_exc()
                raise e
                        
        return AttributesOfPACID(pac_url=pac_url, # return the pac_url as given, i.e. with the extension if there was one
                                 attribute_groups=attribute_groups)
        
    

    def _get_referenced_pac_ids(self, attributes_for_pac:AttributesOfPACID):
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
            
    # def get_translations(self, attributes_for_pac_id): 
    #     ontology_map = {}  # ontology name → list of TermTranslations

    #     for ag_for_pac in attributes_for_pac_id:
    #         for ag in ag_for_pac.attribute_groups:
    #             ag: AttributeGroup
    #             ontology_name = ag.ontology
    #             translation_data_source: TranslationDataSource = self._translation_data_sources.get(ontology_name, {})

    #             attribute_keys = [a.key for a in ag.attributes]
    #             all_keys = set([ag.key] + attribute_keys)

    #             for k in all_keys:
    #                 t = translation_data_source.get_translations_for(k)
    #                 if t:
    #                     ontology_map.setdefault(ontology_name, []).append(t)

    #     translations_by_ontology = [ TranslationsForOntology(ontology=name, terms=terms) for name, terms in ontology_map.items()
    #                                 ]
    #     return translations_by_ontology
    
    
    # def _get_display_name_for_key(self, key, requested_languages:str): 
    #     for tds in self._translation_data_sources:
    #         if term := tds.get_translations_for(key):
    #             # try the languages requested by the user
    #             for l in requested_languages:
    #                 if dn := term.in_language(l):
    #                     return dn
    #             # remove the country codes and try the again
    #             for l_fallback in [l.split('-')[0] for l in requested_languages]:
    #                 if dn := term.in_language(l_fallback):
    #                     return dn
    #             # use the server fallback language
    #             if dn := term.in_language(self._default_language):
    #                 return 
    #     warnings.warn(f'No translation for {key}')
    #     return None
    
    def _add_display_names(self, attributes_of_pac:AttributesOfPACID, language:str) -> str:
        ''' 
        adds the display names in the requested language to attribute group and attributes.
        if no translation can be found in this language it IMMEDIATELY falls back to some - probably inappropriate- magic.
        Note: The server checks for completeness of translations at initialization. Make sure to resolve warnings there and 
        this function should never get into the situation not to find translations.
        '''
        for ag in attributes_of_pac.attribute_groups:
            if dn := self._get_display_name_for_key(ag.key, language):
                ag.label = dn
            else:
                ag.label = ag.key.split('/')[-1]
                rich.print(f"[yellow]WARNING:[/yellow] No translation for '{ag.key}' in '{language}'. Falling back to '{ag.label}'")
            for a in ag.attributes:
                if dn := self._get_display_name_for_key(a.key, language):
                    a.label = dn
                else:
                    a.label = a.key.split('/')[-1]
                    rich.print(f"[yellow]WARNING:[/yellow] No translation for '{a.key}' in '{language}'. Falling back to '{a.label}' ")
                    
            
        
            
            
    
    def _get_display_name_for_key(self, key, language:str): 
        '''call this only with a language you know there is a translation for'''
        for tds in self._translation_data_sources:
            if term := tds.get_translations_for(key):
                return term.in_language(language)    
        warnings.warn(f'No translation for {key}.')
        return None
                
                
    def _find_response_language(self, requested_languages):
        '''finds the language the server will respond in'''
        if not requested_languages:
            return self._default_language
        
        for l in requested_languages:
            if l in self._supported_languages:
                return l
            
        # remove the country codes and try the again
        for l_fallback in [l.split('-')[0] for l in requested_languages]:
            if l in self._supported_languages:
                return l_fallback

        return self._default_language
                
                
        
    def capabilities(self):
        return ServerCapabilities(supported_languages=self._supported_languages,
                                  default_language=self._default_language,
                                  available_attribute_groups= [ds.attribute_group_key for ds in self._attribute_group_data_sources]).model_dump_json()
    

            








    
        
        
        
    

    
    
    
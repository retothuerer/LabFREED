import re
from functools import cached_property
from pathlib import Path
from urllib.parse import urlparse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field
from labfreed.pac_attributes.facade.attributes import Attribute, AttributeGroup, Attributes, Reference, Resource
from labfreed.pac_attributes.well_known_attribute_keys import CommercePackagingKeys, DocumentKeys, IdentifierKeys, MetaAttributeKeys, PhysicoChemicalProperties, RegulatorySafetyKeys
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.pac_cat.predefined_categories import PredefinedCategory
from labfreed.pac_id.pac_id import PAC_ID
from labfreed.pac_id_resolver.services import ServiceGroup, Service
from labfreed.labfreed_extended.app.formatted_print import StringIOLineBreak
from labfreed.trex.facade.data_table import DataTable
from labfreed.trex.facade.t_rex import T_REX
from labfreed.utilities.ghs.ghs_statements import extract_statement_code, hazard_statement_text, hazard_statement_is_complete, precautionary_statement_text, precautionary_statement_is_complete, pictogram_codes_for_hazard_statement, signal_word_for_hazard_statements
from labfreed.utilities.ghs.ghs_statement_models import HazardStatement, PrecautionaryStatement
from labfreed.well_known_extensions.display_name_extension import DisplayNameExtension
from labfreed.labfreed_infrastructure import experimental
from enum import Enum


class Document(BaseModel):
    '''Uniform shape for a document reachable either via an attribute (a Resource/
    link value) or a user handover Service keyed the same way - so a consumer never
    has to branch on which of the two PacInfo.safety_data_sheet (etc.) came from.'''
    name: str
    key: str
    url: str

    @classmethod
    def from_attribute(cls, attribute: Attribute) -> 'Document':
        value = attribute.values
        url = value.root if isinstance(value, Resource) else str(value)
        return cls(name=attribute.label, key=attribute.key, url=url)

    @classmethod
    def from_service(cls, service: Service) -> 'Document':
        return cls(name=service.service_name, key=service.key or '', url=service.url)


# Every well-known key already surfaced by a dedicated PacInfo property below
# (supplier, nominal_quantity, signal_word, ufi, documents (safety_data_sheet/
# certificate_of_analysis included), product_identifiers,
# physico_chemical_properties, specifications, hazard_statements,
# precautionary_statements, safety_pictogram_codes/explicit_pictogram_image_urls) -
# the single place that list is assembled, so PacInfo.other_attribute_groups can
# exclude them without a UI template having to know about every property individually.
_CLAIMED_ATTRIBUTE_KEYS = [
    IdentifierKeys.SUPPLIER,
    CommercePackagingKeys.QUANTITY,
    RegulatorySafetyKeys.GHS_SIGNAL_WORD,
    RegulatorySafetyKeys.UNIQUE_FORMULA_IDENTIFIER,
    *DocumentKeys,
    RegulatorySafetyKeys.CLP_ANNEX_VI_INDEX_NO,
    IdentifierKeys.CAS_NUMBER,
    IdentifierKeys.CAS_NUMBER_ALT,
    IdentifierKeys.EC_NUMBER,
    IdentifierKeys.PRODUCT_CODE,
    IdentifierKeys.SYNONYM,
    IdentifierKeys.EMPIRICAL_FORMULA,
    *PhysicoChemicalProperties,  # includes WATER_CONTENT, claimed by specifications
    RegulatorySafetyKeys.ASSAY,
    "https://identifiers.org/CHEBI:15377",  # water, claimed by specifications alongside WATER_CONTENT
    RegulatorySafetyKeys.HEAVY_METALS,
    RegulatorySafetyKeys.STERILITY,
    RegulatorySafetyKeys.ENDOTOXIN,
    RegulatorySafetyKeys.ACCEPTANCE_QUALITY_LIMIT,
    RegulatorySafetyKeys.GHS_HAZARD_STATEMENT,
    RegulatorySafetyKeys.GHS_PRECAUTIONARY_STATEMENT,
    RegulatorySafetyKeys.GHS_PICTOGRAM,
]


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
    @experimental()
    def supplier(self) -> Attribute | None:
        # value is expected to be a PAC-ID reference to the supplier's own attribute
        # page (their name/address/phone live there) - see design-choices.md
        return self.get_attribute(IdentifierKeys.SUPPLIER)
    
    
    
    @cached_property
    @experimental()
    def hazard_statements(self) -> list[HazardStatement]:
        statements = set()
        for attribute in self.get_attributes(RegulatorySafetyKeys.GHS_HAZARD_STATEMENT):
            for value in attribute.value_list:
                normalized = re.sub(r'\s*\+\s*', '+', value.strip())
                codes = [v for v in re.split(r'[\s;-]+', normalized) if v.startswith('H')]
                for c in codes:
                    code = extract_statement_code(c)
                    statements.add(HazardStatement(code=code,
                                                    text=hazard_statement_text(code),
                                                    text_origin='Predefined',
                                                    complete=hazard_statement_is_complete(code)))
        return sorted(statements, key=lambda s: s.code)

    @cached_property
    @experimental()
    def precautionary_statements(self) -> list[PrecautionaryStatement]:
        statements = set()
        for attribute in self.get_attributes(RegulatorySafetyKeys.GHS_PRECAUTIONARY_STATEMENT):
            for value in attribute.value_list:
                normalized = re.sub(r'\s*\+\s*', '+', value.strip())
                codes = [v for v in re.split(r'[\s;-]+', normalized) if v.startswith('P')]
                for c in codes:
                    code = extract_statement_code(c)
                    statements.add(PrecautionaryStatement(code=code,
                                                            text=precautionary_statement_text(code),
                                                            text_origin='Predefined',
                                                            complete=precautionary_statement_is_complete(code)))
        return sorted(statements, key=lambda s: s.code)


    


    @cached_property
    @experimental()
    def _safety_pictogram_codes_from_attributes(self) -> set[str]:
        # find the codes explicitly given by attributes as bare strings (e.g. "GHS02").
        # Resource-valued (image link) entries are not codes - they're not added here,
        # so they don't get double-rendered; explicit_pictogram_image_urls (below)
        # takes them from GHS_PICTOGRAM attributes as-is instead.
        codes = set()
        for attribute in self.get_attributes(RegulatorySafetyKeys.GHS_PICTOGRAM):
            for value in attribute.value_list:
                if isinstance(value, str):
                    normalized = re.sub(r'\s*\+\s*', '+', value.strip())
                    codes.update(part for part in re.split(r'[\s;-]+', normalized) if part)
        return codes


    @cached_property
    @experimental()
    def safety_pictogram_codes(self) -> list[str]:
        # GHS0x codes explicitly given by GHS_PICTOGRAM attributes, plus codes derived
        # from hazard statement codes via the 06e_annex3 lookup table. Precautionary
        # statements are never a source here - pictogram assignment is per hazard
        # class/category, so P-codes carry none (see signal_word_for_hazard_statements).
        codes = set(self._safety_pictogram_codes_from_attributes)
        for statement in self.hazard_statements:
            codes.update(pictogram_codes_for_hazard_statement(statement))
        return sorted(codes)

    @cached_property
    @experimental()
    def explicit_pictogram_image_urls(self) -> list[str]:
        # supplier-provided pictogram images (Resource-valued GHS_PICTOGRAM attribute
        # values) - rendered as-is, not matched to a specific code (see
        # _safety_pictogram_codes_from_attributes, which handles the string/code case)
        return [str(value.root) for attribute in self.get_attributes(RegulatorySafetyKeys.GHS_PICTOGRAM)
                for value in attribute.value_list if isinstance(value, Resource)]




    @cached_property
    @experimental()
    def signal_word(self) -> str | None:
        # attribute-delivered wins if present (matches the earlier precedence decision
        # for hazard/precautionary statement text); derived from hazard statements
        # (never precautionary - see signal_word_for_hazard_statements) otherwise.
        if attribute := self.get_attribute(RegulatorySafetyKeys.GHS_SIGNAL_WORD):
            return attribute.values
        return signal_word_for_hazard_statements(self.hazard_statements)
    
    
    @cached_property
    @experimental()
    def nominal_quantity(self) -> Attribute | None:
        return self.get_attribute(CommercePackagingKeys.QUANTITY)

    @staticmethod
    def _dedupe_attributes(attributes: list[Attribute]) -> list[Attribute]:
        # get_attribute matches by substring containment (`key in a.key`), so two
        # different well-known keys can both match the same underlying attribute
        # (e.g. MASS_FRACTION's URI is a literal substring of WATER_CONTENT's) -
        # dedupe by the attribute's own key, unique in _all_attributes by construction.
        seen = set()
        out = []
        for a in attributes:
            if a.key not in seen:
                seen.add(a.key)
                out.append(a)
        return out

    @cached_property
    @experimental()
    def product_identifiers(self) -> list[Attribute]:
        # CLP Art. 18 "product identifier": for a substance, its Annex VI/CAS/EC
        # identity; for a mixture, the identity of the substances contributing to its
        # classification. Trade name is already covered by display_name - this is
        # just the chemical/regulatory identifiers, in order of CLP-specific first.
        keys = [
            RegulatorySafetyKeys.CLP_ANNEX_VI_INDEX_NO,
            IdentifierKeys.CAS_NUMBER,
            IdentifierKeys.CAS_NUMBER_ALT,
            IdentifierKeys.EC_NUMBER,
            IdentifierKeys.PRODUCT_CODE,
        ]
        return self._dedupe_attributes([a for key in keys if (a := self.get_attribute(key))])

    @cached_property
    @experimental()
    def synonyms(self) -> list[Attribute]:
        # IdentifierKeys.SYNONYM and MetaAttributeKeys.ALIAS are the same underlying
        # well-known key (schema.org/alternateName) - querying one covers both.
        return self._dedupe_attributes(self.get_attributes(IdentifierKeys.SYNONYM))

    @cached_property
    @experimental()
    def physico_chemical_properties(self) -> list[Attribute]:
        # every PhysicoChemicalProperties key present, wherever it lives among the
        # attribute groups - that enum is already the curated "sensible" key set
        # (boiling/melting point, density, flash point, pH, viscosity, ...), so no
        # separate hand-picked subset/ordering is needed the way product_identifiers
        # needed one (that one spans several enums with a CLP-specific priority order).
        # WATER_CONTENT is excluded by its actual attribute key, not just skipped in
        # the query loop - MASS_FRACTION's URI is a literal substring of
        # WATER_CONTENT's, so querying MASS_FRACTION alone would still leak it back
        # in via get_attribute's substring matching. It reads as a QC/CoA-style spec,
        # not a bulk material property, so it belongs in specifications instead, not both.
        matches = self._dedupe_attributes([a for key in PhysicoChemicalProperties if (a := self.get_attribute(key))])
        matches = [a for a in matches if a.key != PhysicoChemicalProperties.WATER_CONTENT.value]
        # empirical formula leads the list - the chemical identity is the first thing
        # a reader wants when scanning physical/chemical properties, even though it's
        # an IdentifierKeys member, not a PhysicoChemicalProperties one itself.
        if formula := self.get_attribute(IdentifierKeys.EMPIRICAL_FORMULA):
            matches = [formula] + [a for a in matches if a.key != formula.key]
        return matches

    @cached_property
    @experimental()
    def specifications(self) -> list[Attribute]:
        # product/QC specification attributes - the kind of parameter set typically
        # found on a Certificate of Analysis, distinct from physico_chemical_properties'
        # bulk material properties.
        keys = [
            RegulatorySafetyKeys.ASSAY,
            PhysicoChemicalProperties.WATER_CONTENT,
            "https://identifiers.org/CHEBI:15377",  # water content keyed by the substance (ChEBI) rather than the QUDT quantity-kind - some sources use this instead of/alongside WATER_CONTENT
            RegulatorySafetyKeys.HEAVY_METALS,
            RegulatorySafetyKeys.STERILITY,
            RegulatorySafetyKeys.ENDOTOXIN,
            RegulatorySafetyKeys.ACCEPTANCE_QUALITY_LIMIT,
        ]
        return self._dedupe_attributes([a for key in keys if (a := self.get_attribute(key))])

    @cached_property
    @experimental()
    def ufi(self) -> Attribute | None:
        return self.get_attribute(RegulatorySafetyKeys.UNIQUE_FORMULA_IDENTIFIER)
    

    def _get_document(self, key) -> Document | None:
        # attribute (a Resource/link value) takes priority; falls back to a user
        # handover Service keyed the same way - see Document.from_attribute/from_service
        if attribute := self.get_attribute(key):
            return Document.from_attribute(attribute)
        if service := self.get_user_handover_by_key(key):
            return Document.from_service(service)
        return None

    @cached_property
    @experimental()
    def documents(self) -> list[Document]:
        # every DocumentKeys entry (SDS, Certificate of Analysis, Datasheet, User
        # Manual), from either an attribute or a user handover Service keyed the same
        # way - see _get_document. safety_data_sheet/certificate_of_analysis below
        # are just convenience shortcuts into this same set, not a separate source.
        return [doc for key in DocumentKeys if (doc := self._get_document(key))]

    @cached_property
    @experimental()
    def safety_data_sheet(self) -> Document | None:
        return self._get_document(DocumentKeys.SAFETY_DATA_SHEET)

    @cached_property
    @experimental()
    def certificate_of_analysis(self) -> Document | None:
        return self._get_document(DocumentKeys.CERTIFICATE_OF_ANALYSIS)
    


    @cached_property
    @experimental()
    def other_attribute_groups(self) -> dict[str, AttributeGroup]:
        # attribute_groups with every attribute already surfaced by a dedicated
        # property (see _CLAIMED_ATTRIBUTE_KEYS) filtered out of each group - lets a
        # generic "everything else" UI block avoid showing the same attribute twice.
        # Matches get_attribute(s)' own substring-containment semantics (`key in
        # a.key`), just inverted for exclusion. Groups left with nothing remaining
        # are dropped entirely rather than shown empty.
        claimed = [str(key) for key in _CLAIMED_ATTRIBUTE_KEYS]
        out = {}
        for group_key, ag in self.attribute_groups.items():
            remaining = {k: a for k, a in ag.attributes.items()
                         if not any(claim in a.key for claim in claimed)}
            if remaining:
                out[group_key] = ag.model_copy(update={'attributes': remaining})
        return out

    @cached_property
    @experimental()
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
    
    
    

    
    
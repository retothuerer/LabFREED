from enum import Enum


class MetaAttributeKeys(Enum):
    DISPLAYNAME = "https://schema.org/name"
    IMAGE = "https://schema.org/image"
    ALIAS = "https://schema.org/alternateName"
    DESCRIPTION = "https://schema.org/description"
    GROUPKEY = "https://labfreed.org/terms/attribute_group_metadata"

    PHONE = 'https://schema.org/telephone'
    EMAIL = 'https://schema.org/email'
    ADDRESS = 'https://schema.org/address'
    COUNTRY = 'https://schema.org/addressCountry'



class PhysicoChemicalProperties(Enum):
    BOILINGPOINT    = "https://qudt.org/vocab/quantitykind/BoilingPoint"
    MELTINGPOINT    = "https://qudt.org/vocab/quantitykind/MeltingPoint"
    POLARITY        = "https://labfreed.org/dummy/polarity"
    DENSITY         = "https://qudt.org/vocab/quantitykind/Density"
    MOLARMASS       = "https://qudt.org/vocab/quantitykind/MolarMass"
    FLASHPOINT      = "https://qudt.org/vocab/quantitykind/FlashPoint"


class ChemicalIdentifiers(Enum):
    CAS_NUMBER          = "https://registry.identifiers.org/registry/cas"
    EC_NUMBER           = "https://www.wikidata.org/wiki/Property:P232"
    EMPIRICAL_FORMULA   = "https://w3id.org/chemrof/generalized_empirical_formula"


class GuaranteeAnalysisProperties(Enum):
    ASSAY           = "https://doi.org/10.1351/goldbook.08014"
    WATER_CONTENT   = "https://identifiers.org/CHEBI:15377"


class DocumentKeys(Enum):
    DATASHEET           = "https://www.wikidata.org/wiki/Q20819677"
    SAFETY_DATA_SHEET   = "https://www.wikidata.org/wiki/Q222067"

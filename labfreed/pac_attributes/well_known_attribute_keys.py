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
    BOILINGPOINT    = "https://labfreed.org/dummy/boilingpoint"
    MELTINGPOINT    = "https://labfreed.org/dummy/meltingpoint"
    POLARITY        = "https://labfreed.org/dummy/polarity"
    DENSITY         = "https://labfreed.org/dummy/density"

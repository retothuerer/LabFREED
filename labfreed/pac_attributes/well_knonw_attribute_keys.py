from enum import Enum


class MetaAttributeKeys(Enum):
    DISPLAYNAME = "https://schema.org/name"
    IMAGE = "https://schema.org/image"
    ALIAS = "https://schema.org/alternateName"
    DESCRIPTION = "https://schema.org/description"
    GROUPKEY = "https://labfreed.org/terms/attribute_group_metadata"
    
    NAME = "https://schema.org/name"
    PHONE = 'https://schema.org/telephone'
    EMAIL = 'https://schema.org/email'
    ADDRESS = 'https://schema.org/address'
    COUNTRY = 'https://schema.org/addressCountry'
    
    
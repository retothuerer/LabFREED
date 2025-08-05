from enum import Enum


class MetaAttributeKeys(Enum):
    DISPLAYNAME = "https://schema.org/name"
    IMAGE = "https://schema.org/image"
    ALIAS = "https://schema.org/alternateName"
    DESCRIPTION = "https://schema.org/description"
    GROUPKEY = "https://labfreed.org/attribute_metadata_group"
    
    
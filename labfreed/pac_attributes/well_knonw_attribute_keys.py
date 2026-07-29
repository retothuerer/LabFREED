import warnings

from labfreed.pac_attributes.well_known_attribute_keys import MetaAttributeKeys, PhysicoChemicalProperties

warnings.warn(
    "labfreed.pac_attributes.well_knonw_attribute_keys is deprecated (typo in the "
    "module name) - use labfreed.pac_attributes.well_known_attribute_keys instead.",
    DeprecationWarning,
    stacklevel=2,
)

# PhysoChemicalProperties was also a typo (missing "ic") - kept as an alias here for
# anyone still importing it under the old name from this old module path.
PhysoChemicalProperties = PhysicoChemicalProperties

__all__ = ["MetaAttributeKeys", "PhysoChemicalProperties"]

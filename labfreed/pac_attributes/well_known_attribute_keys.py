from enum import StrEnum


class MetaAttributeKeys(StrEnum):
    DISPLAYNAME = "https://schema.org/name"
    IMAGE = "https://schema.org/image"
    ALIAS = "https://schema.org/alternateName"
    DESCRIPTION = "https://schema.org/description"
    LOCATION = "https://schema.org/location"
    
    GROUPKEY = "https://labfreed.org/terms/attribute_group_metadata"

    PHONE = 'https://schema.org/telephone'
    EMAIL = 'https://schema.org/email'
    ADDRESS = 'https://schema.org/address'
    COUNTRY = 'https://schema.org/addressCountry'


class IdentifierKeys(StrEnum):
    CAS_NUMBER              = "https://registry.identifiers.org/registry/cas"
    CAS_NUMBER_ALT          = "https://www.wikidata.org/wiki/Property:P231"
    MDL_NUMBER              = "https://bioregistry.io/registry/mdl"
    EC_NUMBER               = "https://www.wikidata.org/wiki/Property:P232"
    BEILSTEIN_REAXYS_NUMBER = "https://www.wikidata.org/wiki/Property:P1579"
    PUBCHEM_SUBSTANCE_ID    = "https://www.wikidata.org/wiki/Property:P2153"
    UNSPSC_CODE             = "https://www.wikidata.org/wiki/Property:P2167"
    INCHI                   = "https://www.wikidata.org/wiki/Property:P234"
    INCHIKEY                = "https://www.wikidata.org/wiki/Property:P235"
    CHEMICAL_FORMULA        = "https://www.wikidata.org/wiki/Property:P274"
    EMPIRICAL_FORMULA       = "https://w3id.org/chemrof/generalized_empirical_formula"
    SMILES                  = "https://w3id.org/chemrof/smiles_string"
    UN_NUMBER               = "https://www.wikidata.org/wiki/Q908597"
    UNIPROTKB_ACCESSION     = "http://purl.obolibrary.org/obo/NCIT_C47851"
    GENE_IDENTIFIER         = "http://purl.obolibrary.org/obo/NCIT_C48664"
    PRODUCT_CODE            = "https://schema.org/productID"
    SKU                     = "https://schema.org/sku"
    LOT_NUMBER              = "https://schema.org/lotNumber"
    SERIAL_NUMBER           = "https://schema.org/serialNumber"
    SYNONYM                 = "https://schema.org/alternateName"
    SUPPLIER                = "https://schema.org/manufacturer"


class PhysicoChemicalProperties(StrEnum):
    BOILINGPOINT            = "https://qudt.org/vocab/quantitykind/BoilingPoint"
    MELTINGPOINT            = "https://qudt.org/vocab/quantitykind/MeltingPoint"
    POLARITY                = "https://labfreed.org/dummy/polarity"
    DENSITY                 = "https://qudt.org/vocab/quantitykind/Density"
    RELATIVE_DENSITY        = "https://qudt.org/vocab/quantitykind/RelativeMassDensity"
    MOLARMASS               = "https://qudt.org/vocab/quantitykind/MolarMass"
    FLASHPOINT              = "https://qudt.org/vocab/quantitykind/FlashPoint"
    REFRACTIVE_INDEX        = "https://qudt.org/vocab/quantitykind/RefractiveIndex"
    WATER_SOLUBILITY        = "https://qudt.org/vocab/quantitykind/WaterSolubility"
    PH                      = "https://qudt.org/vocab/quantitykind/PH"
    VISCOSITY               = "https://qudt.org/vocab/quantitykind/Viscosity"
    CONCENTRATION           = "https://qudt.org/vocab/quantitykind/AmountOfSubstanceConcentration"
    VOLUME                  = "https://qudt.org/vocab/quantitykind/Volume"
    MASS                    = "https://qudt.org/vocab/quantitykind/Mass"
    LENGTH                  = "https://qudt.org/vocab/quantitykind/Length"
    AREA                    = "https://qudt.org/vocab/quantitykind/Area"
    PRESSURE                = "https://qudt.org/vocab/quantitykind/Pressure"
    AMBIENT_PRESSURE        = "https://qudt.org/vocab/quantitykind/AmbientPressure"
    TEMPERATURE             = "https://qudt.org/vocab/quantitykind/Temperature"
    VOLUME_FLOW_RATE        = "https://qudt.org/vocab/quantitykind/VolumeFlowRate"
    LOG_KOW                 = "https://qudt.org/vocab/quantitykind/LogOctanolWaterPartitionCoefficient"
    VAPOUR_PRESSURE         = "https://qudt.org/vocab/quantitykind/VapourPressure"
    SURFACE_TENSION         = "https://qudt.org/vocab/quantitykind/SurfaceTension"
    SPECIFIC_HEAT_CAPACITY  = "https://qudt.org/vocab/quantitykind/SpecificHeatCapacity"
    CONDUCTIVITY            = "https://qudt.org/vocab/quantitykind/ElectricConductivity"
    MASS_FRACTION           = "https://qudt.org/vocab/quantitykind/MassFraction"
    WATER_CONTENT           = "https://qudt.org/vocab/quantitykind/MassFractionOfWater"
    THICKNESS               = "https://qudt.org/vocab/quantitykind/Thickness"
    GROSS_WEIGHT            = "https://schema.org/weight"


class ChemicalAppearanceProperties(StrEnum):
    AUTOIGNITION_TEMPERATURE   = "https://www.wikidata.org/wiki/Q558378"
    DECOMPOSITION_TEMPERATURE  = "https://www.wikidata.org/wiki/Q113847680"
    ODOUR                      = "https://www.wikidata.org/wiki/Q1971477"
    VAPOUR_DENSITY             = "https://www.wikidata.org/wiki/Q3023279"
    PARTICLE_SIZE              = "https://www.wikidata.org/wiki/Q7140503"
    SURFACE_AREA               = "https://www.wikidata.org/wiki/Q1379273"
    PKA                        = "https://www.wikidata.org/wiki/Q325519"
    SPECIFIC_OPTICAL_ROTATION  = "https://www.wikidata.org/wiki/Q2191631"
    APPEARANCE                 = "https://www.wikidata.org/wiki/Q3620816"
    COLOUR                     = "https://schema.org/color"
    PHYSICAL_STATE             = "http://purl.obolibrary.org/obo/NCIT_C73487"
    MATERIAL                   = "https://schema.org/material"


class RegulatorySafetyKeys(StrEnum):
    GHS_HAZARD_STATEMENT        = "https://www.wikidata.org/wiki/Q28360"
    GHS_PRECAUTIONARY_STATEMENT = "https://www.wikidata.org/wiki/Q2467204"
    GHS_SIGNAL_WORD              = "https://www.wikidata.org/wiki/Q15350855"
    GHS_PICTOGRAM                = "https://www.wikidata.org/wiki/Q19360817"
    UN_HAZARD_CLASS              = "https://www.wikidata.org/wiki/Property:P874"
    UN_PACKING_GROUP             = "https://www.wikidata.org/wiki/Property:P876"
    CLP_ANNEX_VI_INDEX_NO        = "https://www.wikidata.org/wiki/Q12021577"
    WATER_HAZARD_CLASS           = "https://www.wikidata.org/wiki/Q1389895"
    HS_TARIC_CUSTOMS_CODE        = "https://www.wikidata.org/wiki/Q55237506"
    HEAVY_METALS                 = "https://www.wikidata.org/wiki/Q105789"
    ASSAY                        = "https://doi.org/10.1351/goldbook.08014"
    STERILITY                    = "http://purl.obolibrary.org/obo/NCIT_C134278"
    ENDOTOXIN                    = "http://purl.obolibrary.org/obo/NCIT_C50918"
    CE_MARKING                   = "https://www.wikidata.org/wiki/Q467405"
    ISO_STANDARD                 = "https://www.wikidata.org/wiki/Q15087423"
    MEDICAL_DEVICE_CLASS         = "https://www.wikidata.org/wiki/Q6554101"
    ANIMAL_ORIGIN                = "https://www.wikidata.org/wiki/Q629103"
    BSE_TSE                      = "https://www.wikidata.org/wiki/Q154666"
    GMO_STATUS                   = "https://www.wikidata.org/wiki/Q182726"
    HALAL                        = "https://www.wikidata.org/wiki/Q177823"
    KOSHER                       = "https://www.wikidata.org/wiki/Q1076110"
    VEGAN                        = "https://www.wikidata.org/wiki/Q899696"
    ACCEPTANCE_QUALITY_LIMIT     = "https://www.wikidata.org/wiki/Q4672371"
    UNIQUE_FORMULA_IDENTIFIER    = "https://www.wikidata.org/wiki/Q61745460"


class StorageHandlingShippingKeys(StrEnum):
    STORAGE_CONDITION     = "http://purl.obolibrary.org/obo/NCIT_C96145"
    SHIPPING_CONDITION    = "http://purl.obolibrary.org/obo/NCIT_C40353"
    SHELF_LIFE            = "http://purl.obolibrary.org/obo/NCIT_C70855"
    TRANSPORT             = "https://www.wikidata.org/wiki/Q7590"
    PROPER_SHIPPING_NAME  = "https://www.wikidata.org/wiki/Q1436174"
    EXPIRY_DATE           = "https://schema.org/expires"


class BiologyAssayKeys(StrEnum):
    CELL_TYPE                = "http://www.ebi.ac.uk/efo/EFO_0000324"
    SAMPLE_TYPE              = "http://purl.obolibrary.org/obo/NCIT_C210102"
    APPLICATION_TECHNIQUE    = "http://purl.obolibrary.org/obo/NCIT_C60755"
    DNA_POLYMERASE           = "http://purl.obolibrary.org/obo/NCIT_C19172"
    PCR                      = "http://purl.obolibrary.org/obo/NCIT_C17003"
    TRANSFECTION             = "http://purl.obolibrary.org/obo/NCIT_C17209"
    DETECTION_METHOD         = "http://purl.obolibrary.org/obo/CHMO_0001709"
    MOLECULAR_TARGET         = "http://purl.obolibrary.org/obo/NCIT_C16128"
    SPECIES_REACTIVITY       = "https://schema.org/appliesToTaxon"
    BUFFER_SOLUTION          = "https://www.wikidata.org/wiki/Q208465"
    STABILISER               = "https://www.wikidata.org/wiki/Q910592"
    PRESERVATIVE             = "https://www.wikidata.org/wiki/Q274579"
    FOOD_ADDITIVE            = "https://www.wikidata.org/wiki/Q350176"
    PROTEIN                  = "https://www.wikidata.org/wiki/Q8054"
    FATTY_ACID               = "https://www.wikidata.org/wiki/Q61476"
    ENZYME_ACTIVITY          = "https://www.wikidata.org/wiki/Q22035510"
    BACTERIA                 = "https://www.wikidata.org/wiki/Q10876"
    MYCOPLASMA               = "https://www.wikidata.org/wiki/Q210975"
    FUNGI                    = "https://www.wikidata.org/wiki/Q764"
    VIRUS                    = "https://www.wikidata.org/wiki/Q808"
    MICROBIAL_CONTAMINATION  = "https://www.wikidata.org/wiki/Q118218165"


class CommercePackagingKeys(StrEnum):
    BRAND                        = "https://schema.org/brand"
    GRADE                        = "http://purl.obolibrary.org/obo/NCIT_C48309"
    FORMAT                       = "http://purl.obolibrary.org/obo/NCIT_C42761"
    CONTAINER_CLOSURE            = "http://purl.obolibrary.org/obo/NCIT_C113033"
    PACK_SIZE                    = "https://schema.org/numberOfItems"
    SIZE_DESCRIPTOR              = "https://schema.org/size"
    QUANTITY                     = "https://schema.org/quantity"
    PRICE                        = "https://schema.org/price"
    CATEGORY                     = "https://schema.org/category"
    INTENDED_USE                 = "https://schema.org/potentialUse"
    COUNTRY_OF_ORIGIN            = "https://schema.org/countryOfOrigin"
    DISAMBIGUATING_DESCRIPTION   = "https://schema.org/disambiguatingDescription"
    USAGE_INFO                   = "https://schema.org/usageInfo"
    PROTEIN_CONTENT              = "https://schema.org/proteinContent"
    CARBOHYDRATE_CONTENT         = "https://schema.org/carbohydrateContent"
    FAT_CONTENT                  = "https://schema.org/fatContent"
    # No fixed key for anything not covered above - fall back to
    # https://schema.org/additionalProperty/<snake_case_name>


class DocumentKeys(StrEnum):
    SAFETY_DATA_SHEET        = "https://www.wikidata.org/wiki/Q222067"
    CERTIFICATE_OF_ANALYSIS  = "https://www.wikidata.org/wiki/Q1056230"
    DATASHEET                = "https://www.wikidata.org/wiki/Q20819677"
    USER_MANUAL              = "https://www.wikidata.org/wiki/Q1057179"


class EventAttributeKeys(StrEnum):
    ATTENDEE_NAME    = "https://schema.org/name"
    GIVEN_NAME       = "https://schema.org/givenName"
    FAMILY_NAME      = "https://schema.org/familyName"
    COMPANY          = "https://schema.org/affiliation"
    BOOKING_NUMBER   = "https://schema.org/reservationNumber"

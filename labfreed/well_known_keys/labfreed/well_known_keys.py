from enum import StrEnum


class WellKnownKeys(StrEnum):
    GTIN = '01'
    BATCH = '10'
    VARIANT = '20'
    SERIAL = '21'
    ADDITIONAL_IDENTIFIER = '240'
    SECONDARY_SERIAL = '250'
    RUN_ID_ABSOLUTE = 'RNR'
    SAMPLE_ID = 'SMP'
    EXPERIMENT_ID = 'EXP'
    RESULT_ID = 'RST'
    METHOD_ID = 'MTD'
    REPORT_ID = 'RPT'
    TIMESTAMP = 'TS'
    VERSION = 'V'
    
    ISSUER_INDIRECTION = 'II'
    
    MAXWEIGHT = "MAXWEIGHT"
    LASTCALIBRATION = "LASTCAL"
    NOMINALWEIGHT = "NOMINALWEIGHT"
    
    
    def as_url(self) -> str:
        # prefix the enum’s name to point to the description in the web
        return f"labfreed.org/wkk/{self.name}"
    

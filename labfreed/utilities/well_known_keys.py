from enum import Enum


class WellKnownKeys(Enum):
    GTIN = '01'
    BATCH = '10'
    SERIAL = '21'
    ADDITIONAL_IDINTIFIER = '240'
    RUN_ID_ABSOLUTE = 'RNR'
    SAMPLE_ID = 'SMP'
    EXPERIMENT_ID = 'EXP'
    RESULT_ID = 'RST'
    METHOD_ID = 'MTD'
    REPORT_ID = 'RPT'
    TIMESTAMP = 'TS'
    VERSION = 'V'
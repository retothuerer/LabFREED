'''Default resolution for PacInfo.processor_pac_id - see that field's docstring.'''
from labfreed import PAC_CAT
from labfreed.labfreed_extended.app.pac_info.pac_info import PacInfo


def default_processor_from_pac_extraction(pac_info: PacInfo) -> PAC_CAT | None:
    '''Default heuristic: PAC-CAT's own `processor` category (the second category in
    the identifier - PAC-CAT's "second category identifying what system generated/
    manages this record", regardless of its type) re-packaged as its own standalone
    PAC-CAT with the same issuer. This is a convention, not a guarantee - a record is
    not required to carry a processor category at all. Issuers whose convention
    differs, or who need to enrich the result, should inject their own via
    IssuerFlaskAppFactory(processor_from_pac=...).
    '''
    pac_id = pac_info.pac_id
    if not isinstance(pac_id, PAC_CAT):
        return None
    processor = pac_id.processor
    if processor is None:
        return None
    return PAC_CAT.from_categories(issuer=pac_id.issuer, categories=[processor])

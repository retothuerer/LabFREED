from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def add_ga_params(url:str, source:str ) -> str:
    parts = urlparse(url)
    query = parse_qs(parts.query)
    query.update({
        'utm_source': f'PAC.{source}',
        'utm_medium': 'link',
        'utm_campaign': 'handover'
    })
    return urlunparse(parts._replace(query=urlencode(query, doseq=True)))


def add_trace_id_params(url:str, trace_id:str ) -> str:
    parts = urlparse(url)
    query = parse_qs(parts.query)
    query.update({
        'trace_id': trace_id
    })
    return urlunparse(parts._replace(query=urlencode(query, doseq=True)))


from functools import cache
import json
from pathlib import Path
import re

from labfreed.utilities.ghs.ghs_statement_models import HazardStatement

_SIGNAL_WORD_SEVERITY = {'Danger': 2, 'Warning': 1}

# A leading statement code (or several joined by "+", e.g. "H300+H310"), optionally
# followed by a separator run and free-text (e.g. a data source's own copy of the
# statement text) that we discard once the code resolves. "+" only ever joins codes
# into one combined statement - it must never be treated as a code/text separator.
_LEADING_CODE = re.compile(
    r'^\s*([A-Z]+\d+(?:\s*\+\s*[A-Z]+\d+)*)(?:[\s\-;.]+.*)?$'
)


def extract_statement_code(raw: str) -> str:
    '''Pulls the leading H-/P-/EUH-code(s) out of a raw value that may have
    human-readable text appended after a separator - lenient about which separator
    (blank space, "-", ";", "." - any run of these), but "+" is reserved for joining
    codes into one combined statement and is never treated as a separator. Returns
    the raw string unchanged if it doesn't start with a recognizable code.'''
    m = _LEADING_CODE.match(raw)
    if not m:
        return raw
    return re.sub(r'\s*\+\s*', '+', m.group(1))


@cache
def ghs_data() -> dict:
    p = Path(__file__).parent / 'ghs_statements.json'
    with open(p) as f:
        return json.load(f)


@cache
def _pictogram_name_to_code() -> dict[str, str]:
    return {name: code for code, name in ghs_data()['pictograms'].items()}


def hazard_statement_text(code: str, lang: str = 'en') -> str | None:
    '''`lang` is currently always "en" in practice - only English text has been
    transcribed so far - but the JSON is already keyed per-language so additional
    languages can be added without another schema migration. Falls back to English
    if the requested language isn't available for that code yet.'''
    entry = ghs_data()['hazard_statements'].get(code)
    return _localized(entry, lang)


def precautionary_statement_text(code: str, lang: str = 'en') -> str | None:
    entry = ghs_data()['precautionary_statements'].get(code)
    return _localized(entry, lang)


def hazard_statement_is_complete(code: str) -> bool | None:
    '''None if `code` isn't a known hazard statement. All hazard statements are
    complete as printed - Annex 3 defines no supplier-completed placeholders for
    H-codes - but the lookup stays symmetric with precautionary_statement_is_complete.'''
    entry = ghs_data()['hazard_statements'].get(code)
    return entry.get('complete') if entry else None


def precautionary_statement_is_complete(code: str) -> bool | None:
    '''False means the Annex 3 text still has a "..." placeholder (e.g. P264 "Wash ...
    thoroughly after handling.") that the manufacturer/supplier or competent authority
    must complete before the statement is label-ready. None if `code` is unknown.'''
    entry = ghs_data()['precautionary_statements'].get(code)
    return entry.get('complete') if entry else None


def _localized(entry: dict | None, lang: str) -> str | None:
    if not entry:
        return None
    return entry.get(lang) or entry.get('en')


def pictogram_name(ghs_code: str) -> str | None:
    '''e.g. "GHS02" -> "Flame"'''
    return ghs_data()['pictograms'].get(ghs_code)


def pictogram_codes_for_hazard_statement(statement: HazardStatement) -> list[str]:
    '''Resolve one or more GHS0x pictogram codes for a HazardStatement, splitting a
    combined code (e.g. "H300+H310") and taking the union of each constituent's
    pictogram(s). Returns [] if none apply (e.g. H303, H401).'''
    info = ghs_data()['hazard_statement_pictograms']
    name_to_code = _pictogram_name_to_code()
    codes = []
    for part in statement.code.split('+'):
        entry = info.get(part.strip())
        if not entry:
            continue
        for name in entry.get('pictogram') or []:
            ghs_code = name_to_code.get(name)
            if ghs_code and ghs_code not in codes:
                codes.append(ghs_code)
    return codes


def signal_word_for_hazard_statement(statement: HazardStatement) -> str | None:
    '''For a combined code (e.g. "H300+H310"), returns the most severe signal word
    among its constituents ("Danger" beats "Warning").'''
    return signal_word_for_hazard_statements([statement])


def signal_word_for_hazard_statements(statements: 'set[HazardStatement] | list[HazardStatement]') -> str | None:
    '''Signal word only ever derives from hazard statements, never precautionary ones -
    P-codes carry no signal-word/pictogram classification in GHS Annex 3 at all, so
    passing PrecautionaryStatements here would just silently contribute nothing. For a
    combined code (e.g. "H300+H310"), the most severe word wins ("Danger" beats
    "Warning") - both across constituents of one statement and across all statements
    passed in.'''
    info = ghs_data()['hazard_statement_pictograms']
    words = set()
    for statement in statements:
        for part in statement.code.split('+'):
            if word := info.get(part.strip(), {}).get('signal_word'):
                words.add(word)
    if not words:
        return None
    return max(words, key=lambda w: _SIGNAL_WORD_SEVERITY.get(w, 0))

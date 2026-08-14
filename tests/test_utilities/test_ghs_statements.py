import pytest

from labfreed.utilities.ghs.ghs_statements import signal_word_for_hazard_statements
from labfreed.utilities.ghs.ghs_statement_models import HazardStatement


def _hs(code: str) -> HazardStatement:
    return HazardStatement(code=code, text=None, text_origin='Predefined')


def test_signal_word_for_hazard_statements_picks_most_severe():
    # H410 is Warning-only, H300 is Danger - the more severe of the two should win
    # regardless of input order.
    assert signal_word_for_hazard_statements([_hs('H410'), _hs('H300')]) == 'Danger'
    assert signal_word_for_hazard_statements([_hs('H300'), _hs('H410')]) == 'Danger'


def test_signal_word_for_hazard_statements_single_code():
    assert signal_word_for_hazard_statements([_hs('H410')]) == 'Warning'


def test_signal_word_for_hazard_statements_combined_code():
    # a single "+"-combined code is resolved the same way signal_word_for_hazard_statement
    # already resolves it internally
    assert signal_word_for_hazard_statements([_hs('H300+H410')]) == 'Danger'


def test_signal_word_for_hazard_statements_ignores_codes_without_a_signal_word():
    # H362 has no signal_word in hazard_statement_pictograms (null) - it shouldn't
    # crash the max() reduction or count as a "no signal word at all" result on its own
    assert signal_word_for_hazard_statements([_hs('H362'), _hs('H410')]) == 'Warning'


def test_signal_word_for_hazard_statements_empty_or_unknown_returns_none():
    assert signal_word_for_hazard_statements([]) is None
    assert signal_word_for_hazard_statements([_hs('H999')]) is None

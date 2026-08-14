'''
TextBase36Extension.create()/DisplayNameExtension.create() log a warning when an
unexpected `type` is given - both currently interpolate the wrong variable
(`{name}` instead of `{type}`) into a message that talks about `type`. Found
independently while checking an external field-notes brief that flagged
`type='N'` as reading like a name/type conflation - the conflation isn't in the
data model, it's this log message.
'''
import logging

import pytest

from labfreed.well_known_extensions.text_base36_extension import TextBase36Extension
from labfreed.well_known_extensions.display_name_extension import DisplayNameExtension
from labfreed.utilities.base36 import to_base36


def test_text_base36_extension_warns_with_the_type_not_the_name(caplog):
    with caplog.at_level(logging.WARNING):
        TextBase36Extension.create(name="MY_NAME", type="WRONG_TYPE", data=to_base36("hi").root)
    assert "WRONG_TYPE" in caplog.text
    assert "MY_NAME" not in caplog.text


def test_display_name_extension_warns_with_the_type_not_the_name(caplog):
    with caplog.at_level(logging.WARNING):
        DisplayNameExtension.create(name="N", type="WRONG_TYPE", data=to_base36("hi").root)
    assert "WRONG_TYPE" in caplog.text

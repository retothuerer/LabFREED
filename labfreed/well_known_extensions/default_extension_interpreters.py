from .text_base36_extension import TextBase36Extension
from .trex_extension import TREX_Extension

default_extension_interpreters = {
    'TREX': TREX_Extension,
    'TEXT': TextBase36Extension
}
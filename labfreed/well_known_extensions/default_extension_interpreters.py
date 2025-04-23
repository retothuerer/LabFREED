from .display_name_extension import DisplayNameExtension
from .trex_extension import TREX_Extension

default_extension_interpreters = {
    'TREX': TREX_Extension,
    'N': DisplayNameExtension
}
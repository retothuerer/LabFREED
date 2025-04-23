from .pac_id import PAC_ID
from .id_segment import IDSegment
from .extension import Extension

'''@private
From a SW engineering perspective it would be best to have no dependencies from other modules to pac_id.
However from a Python users convenience perspective it is better to have one place where a pac url can be parsed and magically the extensions are in a meaningful type (e.g. TREX in TREX aware format) and categories are known of possible.

>> We have given priority to convenient usage and therefore chose to have dependencies from pac_id to pac_cat and well_known_extensions
'''


__all__ = [
    "PAC_ID",
    "IDSegment",
    "Extension"
]



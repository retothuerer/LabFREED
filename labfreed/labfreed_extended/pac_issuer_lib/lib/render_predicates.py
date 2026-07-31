from urllib.parse import urlparse

from labfreed.pac_attributes.pythonic.py_attributes import pyReference, pyResource
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.trex.pythonic import DataTable


def is_pac_id(v: str) -> bool:
    try:
        # suppress_validation_errors=True: this is called on arbitrary attribute
        # values to decide how to render them, most of which were never meant to be
        # a PAC-ID at all - without it, PAC_CAT.from_url logs a full validation
        # report for every value that merely looks PAC-ID-shaped (e.g. contains a
        # '/', like a unit "g/cm3") before raising, which we then just swallow below.
        PAC_CAT.from_url(v, suppress_validation_errors=True)
        return 'PAC.' in v.upper()
    except Exception:
        return False


def is_url(s) -> bool:
    return isinstance(s, str) and urlparse(s).scheme in ('http', 'https') and bool(urlparse(s).netloc)


def is_image(s) -> bool:
    return (
        isinstance(s, pyResource)
        and s.root.lower().startswith('http')
        and s.root.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tif', '.tiff'))
    )


def is_reference(s) -> bool:
    return is_pac_id(s) or isinstance(s, pyReference)


def is_data_table(value) -> bool:
    return isinstance(value, DataTable)


def title_format(s: str) -> str:
    """Convert snake_case string to NYTimes-style title."""
    return s.replace('_', ' ').title()


render_context_utils = {
    "is_url": is_url,
    "is_data_table": is_data_table,
    "is_image": is_image,
    "is_reference": is_reference,
    "is_pac_id": is_pac_id,
    "title_format": title_format,
    "zip": zip,
}

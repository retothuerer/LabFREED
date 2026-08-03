from urllib.parse import urlparse

import nh3
from markupsafe import Markup

from labfreed.pac_attributes.facade.py_attributes import Reference, Resource
from labfreed.pac_attributes.well_known_attribute_keys import (
    CommercePackagingKeys,
    DocumentKeys,
    IdentifierKeys,
    RegulatorySafetyKeys,
)
from labfreed.pac_cat.pac_cat import PAC_CAT
from labfreed.trex.facade import DataTable
from labfreed.utilities.ghs.ghs_statements import (
    extract_statement_code,
    hazard_statement_text,
    pictogram_codes_for_hazard_statement,
    pictogram_name,
    precautionary_statement_text,
)


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


def _as_url_string(s) -> str | None:
    '''Resource is a RootModel[str] - a URL by construction, but not a str
    instance, so isinstance(s, str) alone misses it entirely.'''
    if isinstance(s, Resource):
        return s.root
    if isinstance(s, str):
        return s
    return None


def is_url(s) -> bool:
    text = _as_url_string(s)
    if text is None:
        return False
    parsed = urlparse(text)
    return parsed.scheme in ('http', 'https') and bool(parsed.netloc)


def is_image(s) -> bool:
    if not isinstance(s, Resource):
        return False
    # Check the URL's path, not the full string - a CDN-style URL's real
    # extension (e.g. carlroth.com's asset URLs) is routinely followed by a long
    # tracking/context query string that would break a suffix check on the raw text.
    path = urlparse(s.root).path
    return path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tif', '.tiff'))


def is_reference(s) -> bool:
    return is_pac_id(s) or isinstance(s, Reference)


def is_data_table(value) -> bool:
    return isinstance(value, DataTable)


def title_format(s: str) -> str:
    """Convert snake_case string to NYTimes-style title."""
    return s.replace('_', ' ').title()


_ALLOWED_INLINE_TAGS = {'sub', 'sup', 'i', 'em', 'pre'}


def render_text(value) -> Markup:
    '''Renders an attribute value as HTML, allowing only a small set of inline
    formatting tags (e.g. "C<sub>6</sub>H<sub>12</sub>") - everything else (script,
    style, event-handler attributes, any other tag) is stripped by nh3's real HTML
    parser, not a regex allowlist. A registered-trademark symbol is always wrapped in
    <sup> even when the source text has no markup around it at all.'''
    text = str(value).replace('®', '<sup>®</sup>')
    return Markup(nh3.clean(text, tags=_ALLOWED_INLINE_TAGS, attributes={}))


def explicit_pictogram_images(pac_info) -> dict[str, str]:
    '''Maps GHS0x code -> image URL from whatever pictogram attributes the data
    source directly supplied (PacInfo.safety_pictograms, keyed like
    "https://labfreed.org/ghs/pictogram/GHS02") - lets a hazard statement row prefer
    an explicitly-supplied pictogram over the code-derived guess from
    pictogram_codes_for_hazard_statement, which is only ever an approximation (see
    developer-docs/design-choices.md).'''
    images = {}
    for a in pac_info.safety_pictograms.values():
        code = a.key.rsplit('/', 1)[-1]
        value = a.values[0] if isinstance(a.values, list) else a.values
        if value is not None:
            images[code] = str(value)
    return images


def hazard_pictogram_codes(pac_info, attributes) -> list[str]:
    '''Union of GHS0x codes explicitly supplied on pac_info and codes derived from
    the given hazard/precautionary statement attributes' values (precautionary
    codes simply contribute nothing - they have no pictogram of their own),
    deduplicated via a set and sorted by GHS number - meant to be shown once above
    the statement table rather than repeated per row.'''
    codes = set(explicit_pictogram_images(pac_info))
    for a in attributes:
        for raw in a.value_list:
            codes.update(pictogram_codes_for_hazard_statement(extract_statement_code(raw)))
    return sorted(codes)


def find_attributes(attribute_groups, keys) -> list:
    """Look up attributes across all of a PacInfo's groups by well-known key,
    in `keys` order - skips any key with no match. Lets a template pull a specific
    handful of attributes (e.g. for a highlighted block) out of whichever group the
    data source happened to put them in, without needing its own group structure."""
    by_key = {a.key: a for ag in attribute_groups.values() for a in ag.attributes.values()}
    return [by_key[k] for k in keys if k in by_key]


render_context_utils = {
    "is_url": is_url,
    "is_data_table": is_data_table,
    "is_image": is_image,
    "is_reference": is_reference,
    "is_pac_id": is_pac_id,
    "title_format": title_format,
    "find_attributes": find_attributes,
    "explicit_pictogram_images": explicit_pictogram_images,
    "hazard_pictogram_codes": hazard_pictogram_codes,
    "render_text": render_text,
    "extract_statement_code": extract_statement_code,
    "hazard_statement_text": hazard_statement_text,
    "precautionary_statement_text": precautionary_statement_text,
    "pictogram_codes_for_hazard_statement": pictogram_codes_for_hazard_statement,
    "pictogram_name": pictogram_name,
    "RegulatorySafetyKeys": RegulatorySafetyKeys,
    "DocumentKeys": DocumentKeys,
    "IdentifierKeys": IdentifierKeys,
    "CommercePackagingKeys": CommercePackagingKeys,
    "zip": zip,
}

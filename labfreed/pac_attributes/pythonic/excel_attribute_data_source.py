from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict

from cachetools import TTLCache, cachedmethod

from labfreed.labfreed_infrastructure import LabFREED_ValidationError
from labfreed.pac_attributes.api_data_models.response import AttributeGroup
from labfreed.pac_attributes.pythonic.py_attributes import pyAttribute, pyAttributes
from labfreed.pac_attributes.server.server import AttributeGroupDataSource
from labfreed.pac_cat.pac_cat import PAC_CAT

try:
    from openpyxl import load_workbook
except ImportError:
    raise ImportError("Please install labfreed with the [extended] extra: pip install labfreed[extended]")

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _get_row_by_first_cell(sheet_rows: List[tuple], match_value: str, base_url: str) -> Optional[Dict[str, object]]:
    if not sheet_rows:
        return None
    headers = sheet_rows[0]
    for row in sheet_rows[1:]:
        if not row:
            continue
        first = str(row[0]).strip() if row[0] is not None else ""
        if first == match_value:
            return {
                base_url + str(headers[i]).strip(): row[i]
                for i in range(1, len(headers))
                if headers[i] is not None
            }
    return None


# ---------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------
class _BaseExcelAttributeDataSource(AttributeGroupDataSource):
    """
    Common mapping logic from Excel rows to AttributeGroup.
    Subclasses implement `_read_rows_and_last_changed()`.
    """

    def __init__(self, *, base_url: str = "", cache_duration_seconds: int = 0, uses_pac_cat_short_form:bool=True, pac_to_key=None, header_mappings=None, **kwargs):
        self._base_url = base_url
        self._uses_pac_cat_short_form = uses_pac_cat_short_form
        self._pac_to_key = pac_to_key
        self._header_mappings = header_mappings or dict()
        # a cache of this instance's own, so a different cache_duration_seconds on
        # another instance can never affect this one (see design-choices.md, "Each
        # Excel data source instance gets its own TTLCache")
        try:
            ttl = int(cache_duration_seconds)
        except Exception:
            ttl = 0
        self._cache = TTLCache(maxsize=128, ttl=ttl)
        super().__init__(**kwargs)

    def is_static(self) -> bool:
        return False

    def _read_rows_and_last_changed(self) -> Tuple[List[tuple], Optional[datetime]]:
        raise NotImplementedError

    @property
    def provides_attributes(self) -> List[str]:
        rows, _ = self._read_rows_and_last_changed()
        if not rows:
            return []
        return [self._base_url + r for r in rows[0][1:]]

    def attributes(self, subject_id:str) -> Optional[AttributeGroup]:
        canonical_url = subject_id
        try:
            # suppress_validation_errors=True: subject_id only has to be an IRI here, not a
            # strictly valid PAC-ID - falling back to the raw input below is the expected,
            # routine case, not something worth logging as an error.
            p = PAC_CAT.from_url(subject_id, suppress_validation_errors=True)
            if p.is_valid:
                canonical_url = p.to_url(use_short_notation=self._uses_pac_cat_short_form, include_extensions=self._include_extensions)
                logging.debug(f'Lookup in Excel of {canonical_url}')
        except LabFREED_ValidationError:
            ... # might as well try to match the original input

        rows, last_changed = self._read_rows_and_last_changed()

        # canonicalization can drop information the sheet is still keyed by (e.g. a
        # tolerated trailing '/' - see design-choices.md "Empty id segments"), so fall
        # back to the raw, as-given input if the canonical form doesn't find a match.
        key = self._pac_to_key(canonical_url) if self._pac_to_key else canonical_url
        d = _get_row_by_first_cell(rows, key, self._base_url)
        if not d and canonical_url != subject_id:
            raw_key = self._pac_to_key(subject_id) if self._pac_to_key else subject_id
            d = _get_row_by_first_cell(rows, raw_key, self._base_url)
        if not d:
            return None
        attributes = [pyAttribute(key= self._header_mappings.get(k, k), value=v) for k, v in d.items() if v is not None]
        return AttributeGroup(
            group_key=self._attribute_group_key,
            attributes=pyAttributes(attributes).to_payload_attributes()
        )


# ---------------------------------------------------------------------
# Local file implementation
# ---------------------------------------------------------------------
class LocalExcelAttributeDataSource(_BaseExcelAttributeDataSource):
    def __init__(self, file_path: str, **kwargs):
        self._file_path = file_path
        super().__init__(**kwargs)

    @cachedmethod(lambda self: self._cache)
    def _read_rows_and_last_changed(self) -> Tuple[List[tuple], Optional[datetime]]:
        logging.info(f"Attempting to load workbook: {self._file_path!r}")

        try:
            wb = load_workbook(
                filename=self._file_path,
                read_only=True,
                data_only=True
            )
            ws = wb.active
            logging.info(f"Workbook opened successfully. Active sheet: {ws.title!r}")

            rows = list(ws.iter_rows(values_only=True))
            logging.info(f"Read {len(rows)} rows from {self._file_path!r}")

            last_changed = wb.properties.modified
            logging.info(f"Workbook 'modified' property: {last_changed}")

            wb.close()
            return rows, last_changed

        except FileNotFoundError:
            logging.error(f"Workbook not found at: {self._file_path!r}", exc_info=True)
            raise
        except PermissionError:
            logging.error(f"Permission denied when accessing: {self._file_path!r}", exc_info=True)
            raise
        except Exception as e:
            logging.exception(f"Unexpected error reading workbook {self._file_path!r}: {e}")
            raise


__all__ = [
    "LocalExcelAttributeDataSource",
]

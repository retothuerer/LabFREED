import pytest
from openpyxl import Workbook

from labfreed.pac_attributes.pythonic.excel_attribute_data_source import LocalExcelAttributeDataSource

TRAILING_SLASH_PAC_ID = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345/"


def _write_workbook(path, key):
    wb = Workbook()
    ws = wb.active
    ws.append(["id", "MfgDate"])
    ws.append([key, "2024-01-01"])
    wb.save(path)


def test_local_excel_data_source_finds_a_trailing_slash_id(tmp_path):
    # same regression class already fixed in Dict_DataSource.attributes(): a trailing-
    # slash id is now a *valid* PAC-ID, so PAC_CAT.from_url(...).to_url() canonicalizes
    # it and drops the slash - if the sheet is keyed by the original, uncanonicalized
    # string (as real-world data often is), a canonical-only lookup misses even though
    # the row is right there. Must fall back to the raw input, same as Dict_DataSource.
    file_path = tmp_path / "attributes.xlsx"
    _write_workbook(file_path, TRAILING_SLASH_PAC_ID)

    source = LocalExcelAttributeDataSource(
        file_path=str(file_path),
        attribute_group_key="instrument",
        cache_duration_seconds=0,
    )
    group = source.attributes(TRAILING_SLASH_PAC_ID)

    assert group is not None
    assert "MfgDate" in group.attributes


def test_local_excel_data_source_does_not_crash_on_a_non_pac_id(tmp_path):
    # a subject_id only has to be an IRI (see design-choices.md, "PAC-ID-Attributes'
    # subject_id accepts any IRI..."); today's bare `except:` happens to swallow this,
    # but the fix should catch LabFREED_ValidationError specifically, not any exception.
    non_pac_iri = "https://example.com/thing?x=1"
    file_path = tmp_path / "attributes.xlsx"
    _write_workbook(file_path, non_pac_iri)

    source = LocalExcelAttributeDataSource(
        file_path=str(file_path),
        attribute_group_key="instrument",
        cache_duration_seconds=0,
    )
    group = source.attributes(non_pac_iri)

    assert group is not None
    assert "MfgDate" in group.attributes

from __future__ import annotations

import pytest

from sdss_sky_residual_quality_audit.exceptions import ArchiveAccessError
from sdss_sky_residual_quality_audit.fetch import build_sample_query, validate_sample_table_columns


def test_build_sample_query_is_deterministic():
    assert build_sample_query(10) == build_sample_query(10)


def test_build_sample_query_contains_order_by_specobjid():
    query = build_sample_query(5)
    assert "ORDER BY specobjid" in query
    assert "TOP 5" in query


def test_build_sample_query_rejects_nonpositive_n():
    with pytest.raises(ArchiveAccessError):
        build_sample_query(0)


def test_validate_sample_table_columns_accepts_complete_set():
    validate_sample_table_columns(["specobjid", "plate", "mjd", "fiberid", "run2d", "class", "z"])


def test_validate_sample_table_columns_rejects_missing():
    with pytest.raises(ArchiveAccessError):
        validate_sample_table_columns(["specobjid", "plate"])

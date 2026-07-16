from __future__ import annotations

import pytest

from sdss_sky_residual_quality_audit.exceptions import ProvenanceError
from sdss_sky_residual_quality_audit.provenance import (
    ManifestRow,
    append_manifest_row,
    get_git_commit,
    read_manifest,
    sha256_bytes,
    sha256_file,
)


def test_sha256_bytes_matches_sha256_file(tmp_path):
    data = b"hello world"
    path = tmp_path / "f.bin"
    path.write_bytes(data)
    assert sha256_bytes(data) == sha256_file(path)


def test_get_git_commit_never_raises(tmp_path):
    result = get_git_commit(tmp_path)
    assert isinstance(result, str)


def test_append_and_read_manifest_roundtrip(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    row = ManifestRow(
        product_id="spec-0001",
        source="SDSS DR17",
        source_url="https://data.sdss.org/example",
        retrieved_utc="2026-07-15T00:00:00Z",
        sha256="abc123",
        file_size_bytes=1000,
        selection_reason="deterministic sample",
        licence_or_terms="SDSS public data policy",
    )
    append_manifest_row(manifest_path, row)
    rows = read_manifest(manifest_path)
    assert len(rows) == 1
    assert rows[0]["product_id"] == "spec-0001"


def test_read_manifest_raises_on_missing_file(tmp_path):
    with pytest.raises(ProvenanceError):
        read_manifest(tmp_path / "nope.csv")

from __future__ import annotations

import json

import pytest

from sdss_sky_residual_quality_audit.exceptions import DataSchemaError
from sdss_sky_residual_quality_audit.results_io import Metric, validate_summary, write_summary


def test_write_summary_writes_valid_json(tmp_path):
    path = tmp_path / "summary.json"
    metrics = [Metric(name="excess_ratio_OI_5577", estimate=1.5, units="dimensionless", sample_size=10)]
    payload = write_summary(
        path, project="sdss-sky-residual-quality-audit", data_kind="demo_synthetic",
        metrics=metrics, provenance={"seed": 20260713}, warnings=[],
    )
    assert path.is_file()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == payload


def test_validate_summary_rejects_missing_keys():
    with pytest.raises(DataSchemaError):
        validate_summary({"project": "x"})


def test_validate_summary_rejects_bad_metric():
    payload = {
        "project": "x", "data_kind": "y", "provenance": {}, "warnings": [],
        "metrics": [{"name": "m"}],
    }
    with pytest.raises(DataSchemaError):
        validate_summary(payload)


def test_metric_to_dict_includes_uncertainty():
    m = Metric(name="m", estimate=1.0, units="u", sample_size=5, uncertainty_low=0.8, uncertainty_high=1.2)
    d = m.to_dict()
    assert d["uncertainty_low"] == 0.8
    assert d["uncertainty_high"] == 1.2

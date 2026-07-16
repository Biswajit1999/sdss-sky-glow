from __future__ import annotations

import pytest

from sdss_sky_residual_quality_audit.config import load_config
from sdss_sky_residual_quality_audit.exceptions import DataSchemaError


def test_load_config_reads_real_analysis_yml():
    config = load_config("config/analysis.yml")
    assert config.project.author == "Biswajit Jana"
    assert 0.0 < config.validation.confidence_level < 1.0
    assert config.execution.seed == 20260713


def test_load_config_raises_on_missing_file(tmp_path):
    with pytest.raises(DataSchemaError):
        load_config(tmp_path / "nope.yml")


def test_load_config_raises_on_missing_section(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text("project:\n  title: x\n", encoding="utf-8")
    with pytest.raises(DataSchemaError):
        load_config(bad)


def test_load_config_rejects_bad_confidence_level(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text(
        """
project: {title: x, repository: y, author: z, curation_status: a, priority: 1}
execution: {seed: 1, output_directory: out, overwrite: false, fail_on_warning: false}
input: {data_mode: m, manifest: a, raw_directory: b, example_directory: c}
validation: {minimum_sample_size: 1, bootstrap_resamples: 10, confidence_level: 1.5}
provenance: {record_environment: true, record_git_commit: true, verify_checksums: true}
""",
        encoding="utf-8",
    )
    with pytest.raises(DataSchemaError):
        load_config(bad)

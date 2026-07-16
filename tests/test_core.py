from __future__ import annotations

import numpy as np
import pytest

from sdss_sky_residual_quality_audit.core import bootstrap_aggregate_ratio, process_spectrum, run_pipeline
from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.synthetic import make_synthetic_sample, make_synthetic_spectrum
from sdss_sky_residual_quality_audit.windows import SKY_WINDOW_PAIRS


def test_run_pipeline_empty_input_raises() -> None:
    with pytest.raises(InsufficientDataError):
        run_pipeline([])


def test_run_pipeline_injection_recovery_gate() -> None:
    """Injection-recovery validation gate: a known injected excess-noise bump
    in the OI_5577 sky window should be recovered as an elevated ratio there,
    while it should not appear for the untouched window pairs."""
    inject_window = SKY_WINDOW_PAIRS[0].sky
    spectra = make_synthetic_sample(n_spectra=8, inject_window=inject_window, inject_excess_factor=4.0)
    result = run_pipeline(spectra)

    injected_ratios = [e.ratio for e in result.per_spectrum_excess if e.label == SKY_WINDOW_PAIRS[0].label]
    other_ratios = [e.ratio for e in result.per_spectrum_excess if e.label == SKY_WINDOW_PAIRS[1].label]

    assert injected_ratios, "expected excess statistics for the injected window pair"
    assert other_ratios, "expected excess statistics for an uninjected window pair"
    assert np.median(injected_ratios) > 1.5, "injected excess was not recovered as an elevated ratio"
    assert np.median(other_ratios) < 1.5, "an uninjected window pair should not show a spurious excess"


def test_run_pipeline_null_control_no_excess() -> None:
    """Null-control test: with no injection at all, every window-pair ratio
    should be centred near 1 (no excess) within a generous tolerance."""
    spectra = make_synthetic_sample(n_spectra=8, inject_window=None)
    result = run_pipeline(spectra)
    for label, agg in result.aggregate.items():
        assert 0.5 < agg.median_ratio < 2.0, f"{label}: unexpected excess with no injection ({agg.median_ratio})"


def test_run_pipeline_tolerates_bad_spectrum() -> None:
    """A single degenerate spectrum (all-zero ivar) should produce warnings,
    not abort the whole run."""
    good = make_synthetic_spectrum(seed=1, source_id="SYNTH_GOOD")
    bad = make_synthetic_spectrum(seed=2, source_id="SYNTH_BAD")
    bad = bad.__class__(**{**bad.__dict__, "ivar": np.zeros_like(bad.ivar)})
    result = run_pipeline([good, bad])
    assert result.n_spectra_used >= 1
    assert any("SYNTH_BAD" in w for w in result.warnings)


def test_process_spectrum_returns_excess_and_warnings() -> None:
    spectrum = make_synthetic_spectrum(seed=5)
    excesses, warnings = process_spectrum(spectrum)
    assert isinstance(excesses, list)
    assert isinstance(warnings, list)
    assert len(excesses) == len(SKY_WINDOW_PAIRS)


def test_bootstrap_aggregate_ratio_deterministic() -> None:
    spectra = make_synthetic_sample(n_spectra=6, inject_window=SKY_WINDOW_PAIRS[0].sky, inject_excess_factor=3.0)
    result = run_pipeline(spectra)
    label = SKY_WINDOW_PAIRS[0].label
    boot1 = bootstrap_aggregate_ratio(result.per_spectrum_excess, label, seed=20260713)
    boot2 = bootstrap_aggregate_ratio(result.per_spectrum_excess, label, seed=20260713)
    assert boot1.lower == boot2.lower
    assert boot1.upper == boot2.upper
    assert boot1.lower <= boot1.estimate <= boot1.upper


def test_bootstrap_aggregate_ratio_insufficient_data() -> None:
    with pytest.raises(InsufficientDataError):
        bootstrap_aggregate_ratio([], "OI_5577")

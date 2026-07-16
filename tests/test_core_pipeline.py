from __future__ import annotations

import pytest

from sdss_sky_residual_quality_audit.core import bootstrap_aggregate_ratio, run_pipeline
from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.synthetic import make_synthetic_sample
from sdss_sky_residual_quality_audit.windows import SKY_WINDOW_PAIRS

INJECT_PAIR = SKY_WINDOW_PAIRS[0]  # OI_5577


def test_run_pipeline_raises_on_empty_input():
    with pytest.raises(InsufficientDataError):
        run_pipeline([])


def test_run_pipeline_injection_recovery_gate():
    """Known-answer validation gate: a synthetic sample with a known injected
    excess-noise bump in the OI_5577 sky window must show a materially
    elevated median ratio for that window's aggregate, while an otherwise
    identical uninjected sample must not.
    """
    injected = make_synthetic_sample(
        n_spectra=12, inject_window=INJECT_PAIR.sky, inject_excess_factor=4.0
    )
    clean = make_synthetic_sample(n_spectra=12, inject_window=None)

    result_injected = run_pipeline(injected, window_pairs=(INJECT_PAIR,))
    result_clean = run_pipeline(clean, window_pairs=(INJECT_PAIR,))

    injected_ratio = result_injected.aggregate[INJECT_PAIR.label].median_ratio
    clean_ratio = result_clean.aggregate[INJECT_PAIR.label].median_ratio

    assert injected_ratio > 2.0
    assert 0.5 < clean_ratio < 2.0
    assert injected_ratio > clean_ratio


def test_run_pipeline_records_warnings_not_crash_on_bad_spectrum():
    from sdss_sky_residual_quality_audit.synthetic import make_synthetic_spectrum
    import numpy as np

    good_spectra = make_synthetic_sample(n_spectra=5)
    bad = make_synthetic_spectrum(source_id="SYNTH_BAD")
    bad_flux = bad.flux.copy()
    bad_flux[:] = np.nan
    from dataclasses import replace

    bad_broken = replace(bad, flux=bad_flux)

    result = run_pipeline(good_spectra + [bad_broken])
    assert result.n_spectra_in == 6
    assert any("SYNTH_BAD" in w for w in result.warnings)


def test_bootstrap_aggregate_ratio_matches_bootstrap_statistic():
    spectra = make_synthetic_sample(n_spectra=10, inject_window=INJECT_PAIR.sky, inject_excess_factor=3.0)
    result = run_pipeline(spectra, window_pairs=(INJECT_PAIR,))
    bootstrap_result = bootstrap_aggregate_ratio(result.per_spectrum_excess, INJECT_PAIR.label)
    assert bootstrap_result.lower <= bootstrap_result.estimate <= bootstrap_result.upper


def test_bootstrap_aggregate_ratio_raises_on_missing_label():
    with pytest.raises(InsufficientDataError):
        bootstrap_aggregate_ratio([], "NO_SUCH_LABEL")

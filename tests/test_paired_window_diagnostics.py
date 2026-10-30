"""Paired resampling, null calibration and multiplicity regression tests."""
import numpy as np
import pytest

from sdss_sky_residual_quality_audit.paired_window_diagnostics import (
    diagnostic_report, holm_adjust, leave_one_spectrum_out,
    paired_bootstrap, sign_flip_pvalues,
)


def test_constant_ratio_is_exact_in_bootstrap():
    arr = np.tile([1.5, 0.8], (12, 1))
    result = paired_bootstrap(arr, n_resamples=200)
    assert result["median_ratio"] == pytest.approx([1.5, 0.8])
    assert result["lower_ratio"] == pytest.approx([1.5, 0.8])
    assert result["upper_ratio"] == pytest.approx([1.5, 0.8])


def test_common_rows_preserve_cross_window_bootstrap_dependence():
    rng = np.random.default_rng(5)
    common = rng.normal(0, 0.3, 40)
    arr = np.exp(np.column_stack((common, common)))
    draws = paired_bootstrap(arr, n_resamples=300)["draws_log"]
    assert np.array_equal(draws[:, 0], draws[:, 1])


def test_bootstrap_seed_reproducible_and_missing_values_allowed():
    arr = np.exp(np.arange(45).reshape(15, 3) / 100)
    arr[0, 0] = np.nan
    a = paired_bootstrap(arr, seed=3, n_resamples=200)
    b = paired_bootstrap(arr, seed=3, n_resamples=200)
    assert np.array_equal(a["draws_log"], b["draws_log"], equal_nan=True)


def test_leave_one_out_flags_one_influential_spectrum():
    arr = np.exp(np.array([[0.0], [0.0], [0.0], [0.2], [1.0]]))
    result = leave_one_spectrum_out(arr)
    assert result["max_abs_delta_log"].shape == (1,)
    assert np.all(np.isfinite(result["delta_log"]))
    assert result["full_log_median"][0] == pytest.approx(0)
    assert result["max_abs_delta_log"][0] == pytest.approx(0.1)


def test_exact_sign_flip_two_sided_known_probability():
    arr = np.exp(np.ones((6, 1)))
    p = sign_flip_pvalues(arr)
    assert p[0] == pytest.approx(2 / 64)


def test_sign_flip_all_zero_is_one():
    arr = np.ones((10, 2))
    assert sign_flip_pvalues(arr) == pytest.approx([1.0, 1.0])


def test_seeded_monte_carlo_signflip_detects_large_effect():
    arr = np.exp(np.ones((25, 1)))
    a = sign_flip_pvalues(arr, seed=7, n_resamples=1000)
    b = sign_flip_pvalues(arr, seed=7, n_resamples=1000)
    assert np.array_equal(a, b)
    assert 0 < a[0] < 0.01


def test_holm_adjustment_is_monotone_and_controls_family():
    p = np.array([0.04, 0.001, 0.02, 0.5])
    adjusted = holm_adjust(p)
    assert adjusted == pytest.approx([0.08, 0.004, 0.06, 0.5])
    assert np.all(adjusted >= p)


def test_bad_ratios_and_probabilities_rejected():
    with pytest.raises(ValueError):
        paired_bootstrap(np.array([[1], [0], [2]]))
    with pytest.raises(ValueError):
        sign_flip_pvalues(np.array([[1], [np.inf], [2]]))
    with pytest.raises(ValueError):
        holm_adjust(np.array([1.1]))


def test_diagnostic_has_five_declared_windows():
    result = diagnostic_report()
    assert len(result["median_ratio"]) == 5
    assert len(result["holm_adjusted_p"]) == 5
    assert all(0 <= p <= 1 for p in result["holm_adjusted_p"])

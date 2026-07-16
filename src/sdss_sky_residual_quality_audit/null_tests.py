"""Null-control validation checks for the sky-vs-control excess statistic.

The shifted-window null test places two "control-like" windows (neither
coincident with a documented sky line) at matched positions and compares
their residual scales exactly as `metrics.pair_excess_statistic` compares a
sky window to its control -- since neither window contains a true sky line,
the resulting ratio/difference distribution should be centred near 1 / 0.
A material excess here would indicate a systematic (e.g. continuum-fit bias)
unrelated to night-sky wavelengths, invalidating a naive read of the main
result.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sdss_sky_residual_quality_audit.continuum import fit_local_continuum
from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.metrics import PairExcess, pair_excess_statistic
from sdss_sky_residual_quality_audit.residuals import normalised_residuals, window_residual_statistic
from sdss_sky_residual_quality_audit.windows import Window, WindowPair


def build_shifted_null_pair(pair: WindowPair, shift: float = 200.0) -> WindowPair:
    """Build a null-test window pair from `pair.control`, shifted away from any sky line.

    Both resulting windows are matched-control-style windows (same width),
    with no documented sky line inside either -- unlike `pair.sky`.
    """
    base = pair.control
    null_a = Window(f"{pair.label}_null_a", base.low, base.high)
    null_b = base.shifted(shift, suffix="_null_b")
    return WindowPair(
        label=f"{pair.label}_null",
        sky=null_a,
        control=null_b,
        citation_note="Synthetic null test: neither window coincides with a documented sky line.",
    )


def evaluate_null_pair(
    source_id: str,
    wavelength: np.ndarray,
    flux: np.ndarray,
    ivar: np.ndarray,
    good_mask: np.ndarray,
    null_pair: WindowPair,
    *,
    baseline_halfwidth: float = 100.0,
    degree: int = 1,
) -> PairExcess:
    """Run the sky-vs-control excess statistic on a shifted null-test window pair."""
    fit_a = fit_local_continuum(
        wavelength, flux, ivar, good_mask, null_pair.sky,
        baseline_halfwidth=baseline_halfwidth, degree=degree,
    )
    fit_b = fit_local_continuum(
        wavelength, flux, ivar, good_mask, null_pair.control,
        baseline_halfwidth=baseline_halfwidth, degree=degree,
    )
    resid_a = normalised_residuals(wavelength, flux, ivar, good_mask, fit_a)
    resid_b = normalised_residuals(wavelength, flux, ivar, good_mask, fit_b)
    stat_a = window_residual_statistic(wavelength, resid_a, null_pair.sky)
    stat_b = window_residual_statistic(wavelength, resid_b, null_pair.control)
    return pair_excess_statistic(null_pair.label, source_id, stat_a, stat_b)


@dataclass(frozen=True)
class NullTestSummary:
    label: str
    n_spectra: int
    median_ratio: float
    passed: bool
    tolerance: float


def summarise_null_test(
    excesses: list[PairExcess], *, expected_ratio: float = 1.0, tolerance: float = 0.25
) -> NullTestSummary:
    """Summarise a null test: passes if the median ratio is within `tolerance` of 1.0."""
    if not excesses:
        raise InsufficientDataError("no null-test PairExcess entries supplied")
    ratios = np.array([e.ratio for e in excesses], dtype=float)
    median_ratio = float(np.median(ratios))
    passed = abs(median_ratio - expected_ratio) <= tolerance
    return NullTestSummary(
        label=excesses[0].label,
        n_spectra=len(excesses),
        median_ratio=median_ratio,
        passed=passed,
        tolerance=tolerance,
    )

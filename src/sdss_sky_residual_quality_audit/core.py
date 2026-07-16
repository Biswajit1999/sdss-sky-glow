"""Pipeline orchestration: per-spectrum sky-vs-control excess statistics.

`run_pipeline` is the single entry point scripts/run_analysis.py calls for
both `--demo` (synthetic) and real-data runs. Per-spectrum failures
(`InsufficientDataError`, `ConvergenceError`, `DataSchemaError`) are caught
and converted to warning strings rather than aborting the whole run; an
empty input list raises `InsufficientDataError` immediately.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sdss_sky_residual_quality_audit.bootstrap import BootstrapResult, bootstrap_statistic
from sdss_sky_residual_quality_audit.continuum import fit_local_continuum
from sdss_sky_residual_quality_audit.exceptions import (
    ConvergenceError,
    DataSchemaError,
    InsufficientDataError,
)
from sdss_sky_residual_quality_audit.io import Spectrum
from sdss_sky_residual_quality_audit.masks import good_pixel_mask
from sdss_sky_residual_quality_audit.metrics import AggregateExcess, PairExcess, aggregate_excess, pair_excess_statistic
from sdss_sky_residual_quality_audit.residuals import normalised_residuals, window_residual_statistic
from sdss_sky_residual_quality_audit.windows import SKY_WINDOW_PAIRS, WindowPair, pair_within_range

# --- Minimal deterministic starter functions (kept for the original smoke test) ---


@dataclass(frozen=True)
class Summary:
    count: int
    median: float
    mad: float


def validate_numeric(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError("values must be one-dimensional")
    if arr.size == 0:
        raise ValueError("values must not be empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError("values contain non-finite entries")
    return arr


def robust_summary(values: np.ndarray) -> Summary:
    arr = validate_numeric(values)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    return Summary(count=int(arr.size), median=median, mad=mad)


def demo_series(seed: int = 20260713, size: int = 128) -> np.ndarray:
    """Return deterministic synthetic data labelled only for smoke testing."""
    if size < 8:
        raise ValueError("size must be at least 8")
    rng = np.random.default_rng(seed)
    return rng.normal(loc=0.0, scale=1.0, size=size)


# --- Scientific pipeline ---


@dataclass
class PipelineResult:
    per_spectrum_excess: list[PairExcess] = field(default_factory=list)
    aggregate: dict[str, AggregateExcess] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    n_spectra_in: int = 0
    n_spectra_used: int = 0


def process_spectrum(
    spectrum: Spectrum,
    window_pairs: tuple[WindowPair, ...] = SKY_WINDOW_PAIRS,
    *,
    baseline_halfwidth: float = 100.0,
    degree: int = 1,
) -> tuple[list[PairExcess], list[str]]:
    """Run all window-pair excess statistics for one spectrum.

    Returns `(excesses, warnings)`; a window pair that fails for this
    spectrum (out of range, insufficient baseline pixels, etc.) produces a
    warning string and is skipped, never aborting the whole spectrum.
    """
    excesses: list[PairExcess] = []
    local_warnings: list[str] = []

    good = good_pixel_mask(spectrum.flux, spectrum.ivar, spectrum.and_mask)
    wl_min = float(np.nanmin(spectrum.wavelength))
    wl_max = float(np.nanmax(spectrum.wavelength))

    for pair in window_pairs:
        try:
            if not pair_within_range(pair, wl_min, wl_max):
                local_warnings.append(
                    f"{spectrum.source_id}/{pair.label}: window pair outside spectrum "
                    f"wavelength range [{wl_min:.1f}, {wl_max:.1f}]"
                )
                continue

            sky_fit = fit_local_continuum(
                spectrum.wavelength, spectrum.flux, spectrum.ivar, good, pair.sky,
                baseline_halfwidth=baseline_halfwidth, degree=degree,
            )
            control_fit = fit_local_continuum(
                spectrum.wavelength, spectrum.flux, spectrum.ivar, good, pair.control,
                baseline_halfwidth=baseline_halfwidth, degree=degree,
            )
            sky_resid = normalised_residuals(
                spectrum.wavelength, spectrum.flux, spectrum.ivar, good, sky_fit
            )
            control_resid = normalised_residuals(
                spectrum.wavelength, spectrum.flux, spectrum.ivar, good, control_fit
            )
            sky_stat = window_residual_statistic(spectrum.wavelength, sky_resid, pair.sky)
            control_stat = window_residual_statistic(
                spectrum.wavelength, control_resid, pair.control
            )
            excess = pair_excess_statistic(
                pair.label, spectrum.source_id, sky_stat, control_stat
            )
            excesses.append(excess)
        except (InsufficientDataError, ConvergenceError, DataSchemaError) as exc:
            local_warnings.append(f"{spectrum.source_id}/{pair.label}: {exc}")
            continue

    return excesses, local_warnings


def run_pipeline(
    spectra: list[Spectrum],
    window_pairs: tuple[WindowPair, ...] = SKY_WINDOW_PAIRS,
    *,
    baseline_halfwidth: float = 100.0,
    degree: int = 1,
    bootstrap_seed: int = 20260713,
) -> PipelineResult:
    """Orchestrate the full sky-vs-control excess analysis over a list of spectra.

    Raises `InsufficientDataError` immediately if `spectra` is empty. Any
    single spectrum that fails entirely (e.g. malformed data) is caught and
    recorded as a warning; the run continues with the remaining spectra.
    """
    if not spectra:
        raise InsufficientDataError("run_pipeline received an empty spectrum list")

    result = PipelineResult(n_spectra_in=len(spectra))
    all_excesses: list[PairExcess] = []

    for spectrum in spectra:
        try:
            excesses, warns = process_spectrum(
                spectrum, window_pairs, baseline_halfwidth=baseline_halfwidth, degree=degree
            )
            result.warnings.extend(warns)
            if excesses:
                all_excesses.extend(excesses)
                result.n_spectra_used += 1
        except (InsufficientDataError, ConvergenceError, DataSchemaError) as exc:
            result.warnings.append(f"{spectrum.source_id}: spectrum skipped entirely: {exc}")
            continue

    result.per_spectrum_excess = all_excesses

    for pair in window_pairs:
        try:
            result.aggregate[pair.label] = aggregate_excess(pair.label, all_excesses)
        except InsufficientDataError as exc:
            result.warnings.append(f"aggregate/{pair.label}: {exc}")

    if not all_excesses:
        result.warnings.append("no window-pair excess statistics could be computed for any spectrum")

    return result


def bootstrap_aggregate_ratio(
    excesses: list[PairExcess], label: str, *, seed: int = 20260713
) -> BootstrapResult:
    """Spectrum-level bootstrap confidence interval on the median ratio for one window-pair label."""
    ratios = np.array([e.ratio for e in excesses if e.label == label], dtype=float)
    if ratios.size < 2:
        raise InsufficientDataError(
            f"bootstrap_aggregate_ratio: fewer than 2 spectra with label '{label}'"
        )
    return bootstrap_statistic(ratios, statistic=np.median, seed=seed)

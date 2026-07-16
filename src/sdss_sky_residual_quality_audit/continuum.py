"""Robust local continuum estimation around a wavelength window.

A low-order, inverse-variance-weighted polynomial is fit to a baseline region
that *surrounds but excludes* the window of interest, so that the window's
own pixels never influence the continuum used to compute its residuals. The
wavelength axis is normalised to O(1) before fitting (`x_center`/`x_scale`)
to avoid the structural ill-conditioning that comes from fitting a polynomial
directly in raw Angstrom units (~5000-9000), matching the project-wide
convention documented in docs/VALIDATION_CONTRACT.md / IMPLEMENTATION_PLAN.md.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.windows import Window


@dataclass(frozen=True)
class ContinuumFit:
    coeffs: np.ndarray
    covariance: np.ndarray
    x_center: float
    x_scale: float
    degree: int
    n_points: int


def fit_local_continuum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    ivar: np.ndarray,
    good_mask: np.ndarray,
    window: Window,
    *,
    baseline_halfwidth: float = 100.0,
    degree: int = 1,
) -> ContinuumFit:
    """Fit an ivar-weighted polynomial continuum to the baseline around `window`.

    The baseline is `[window.low - baseline_halfwidth, window.high +
    baseline_halfwidth]` with the window itself excluded. Raises
    `InsufficientDataError` if too few good baseline pixels remain to
    constrain the requested polynomial degree.
    """
    wavelength = np.asarray(wavelength, dtype=float)
    flux = np.asarray(flux, dtype=float)
    ivar = np.asarray(ivar, dtype=float)
    good_mask = np.asarray(good_mask, dtype=bool)

    lo = window.low - baseline_halfwidth
    hi = window.high + baseline_halfwidth
    in_baseline = (wavelength >= lo) & (wavelength <= hi)
    in_window = (wavelength >= window.low) & (wavelength <= window.high)
    selection = in_baseline & ~in_window & good_mask

    n_min = 2 * (degree + 1)
    n_selected = int(np.sum(selection))
    if n_selected < n_min:
        raise InsufficientDataError(
            f"window '{window.name}': only {n_selected} good baseline pixels available, "
            f"need >= {n_min} for a degree-{degree} continuum fit"
        )

    x = wavelength[selection]
    y = flux[selection]
    w = ivar[selection]

    x_center = float(np.mean(x))
    x_scale = float(np.std(x)) or 1.0
    x_norm = (x - x_center) / x_scale
    weights = np.sqrt(np.clip(w, 0.0, None))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", np.RankWarning)
        coeffs, cov = np.polyfit(x_norm, y, degree, w=weights, cov=True)

    return ContinuumFit(
        coeffs=coeffs,
        covariance=np.asarray(cov, dtype=float),
        x_center=x_center,
        x_scale=x_scale,
        degree=degree,
        n_points=n_selected,
    )


def evaluate_continuum(fit: ContinuumFit, wavelength: np.ndarray) -> np.ndarray:
    """Evaluate a `ContinuumFit` at arbitrary wavelength(s)."""
    wavelength = np.asarray(wavelength, dtype=float)
    x_norm = (wavelength - fit.x_center) / fit.x_scale
    return np.polyval(fit.coeffs, x_norm)

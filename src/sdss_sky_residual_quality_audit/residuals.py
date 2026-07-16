"""Per-pixel uncertainty-normalised residuals and per-window aggregate statistics.

The core residual definition for this project's scientific question:
`r_i = (flux_i - continuum_i) * sqrt(ivar_i)`, i.e. the flux excess over the
local continuum expressed in units of the pipeline's own flux uncertainty.
Under correct noise/continuum modelling this should behave like a
zero-mean, unit-scale quantity; the analysis asks whether its scale is
inflated inside known night-sky windows relative to matched control windows.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sdss_sky_residual_quality_audit.continuum import ContinuumFit, evaluate_continuum
from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.windows import Window


@dataclass(frozen=True)
class WindowResiduals:
    window_name: str
    residuals: np.ndarray
    n_pixels: int
    robust_std: float
    rms: float


def normalised_residuals(
    wavelength: np.ndarray,
    flux: np.ndarray,
    ivar: np.ndarray,
    good_mask: np.ndarray,
    fit: ContinuumFit,
) -> np.ndarray:
    """Per-pixel uncertainty-normalised residual for all supplied pixels.

    Pixels where `good_mask` is False are set to `nan` rather than dropped,
    so the returned array stays aligned with `wavelength`.
    """
    wavelength = np.asarray(wavelength, dtype=float)
    flux = np.asarray(flux, dtype=float)
    ivar = np.asarray(ivar, dtype=float)
    good_mask = np.asarray(good_mask, dtype=bool)

    continuum = evaluate_continuum(fit, wavelength)
    sigma = np.full_like(flux, np.nan)
    positive = ivar > 0
    sigma[positive] = 1.0 / np.sqrt(ivar[positive])

    residual = np.full_like(flux, np.nan)
    valid = good_mask & positive & np.isfinite(flux) & np.isfinite(continuum)
    residual[valid] = (flux[valid] - continuum[valid]) * np.sqrt(ivar[valid])
    return residual


def robust_std(values: np.ndarray) -> float:
    """MAD-based robust standard deviation estimate (1.4826 * MAD), NaN-safe."""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    median = np.median(arr)
    mad = np.median(np.abs(arr - median))
    return float(1.4826 * mad)


def window_residual_statistic(
    wavelength: np.ndarray,
    residual: np.ndarray,
    window: Window,
    *,
    min_pixels: int = 3,
) -> WindowResiduals:
    """Aggregate per-pixel residuals inside `window` into robust scale statistics.

    Raises `InsufficientDataError` if fewer than `min_pixels` finite,
    in-window residuals are available.
    """
    wavelength = np.asarray(wavelength, dtype=float)
    residual = np.asarray(residual, dtype=float)
    in_window = (wavelength >= window.low) & (wavelength <= window.high)
    values = residual[in_window]
    values = values[np.isfinite(values)]

    if values.size < min_pixels:
        raise InsufficientDataError(
            f"window '{window.name}': only {values.size} finite residual pixels, "
            f"need >= {min_pixels}"
        )

    rms = float(np.sqrt(np.mean(values**2)))
    return WindowResiduals(
        window_name=window.name,
        residuals=values,
        n_pixels=int(values.size),
        robust_std=robust_std(values),
        rms=rms,
    )

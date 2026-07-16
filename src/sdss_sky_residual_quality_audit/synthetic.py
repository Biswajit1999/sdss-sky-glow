"""Synthetic SDSS-like spectrum generator with known injected residual structure.

Used by `tests/conftest.py` fixtures (injection-recovery validation gate) and
by `scripts/run_analysis.py --demo`. Synthetic spectra are clearly labelled
(`source_id` prefixed `SYNTH_`) and must never be presented as real SDSS
data.
"""
from __future__ import annotations

import numpy as np

from sdss_sky_residual_quality_audit.io import Spectrum
from sdss_sky_residual_quality_audit.windows import Window

WAVELENGTH_MIN = 3900.0
WAVELENGTH_MAX = 9100.0


def make_synthetic_spectrum(
    seed: int = 20260713,
    *,
    source_id: str = "SYNTH_0000",
    n_pixels: int = 4000,
    continuum_level: float = 20.0,
    continuum_slope: float = -0.0005,
    noise_sigma: float = 1.0,
    inject_window: Window | None = None,
    inject_excess_factor: float = 3.0,
    obj_class: str = "GALAXY",
) -> Spectrum:
    """Build a deterministic synthetic `Spectrum`.

    A smooth linear continuum plus Gaussian noise with `ivar = 1/noise_sigma^2`
    everywhere. If `inject_window` is given, pixels inside it get their noise
    scale inflated by `inject_excess_factor` (flux perturbation drawn with a
    larger sigma) -- a known, quantifiable ground-truth excess used to test
    that the pipeline recovers an elevated residual scale in that window and
    nowhere else (injection-recovery gate).
    """
    rng = np.random.default_rng(seed)
    wavelength = np.linspace(WAVELENGTH_MIN, WAVELENGTH_MAX, n_pixels)
    continuum = continuum_level + continuum_slope * (wavelength - WAVELENGTH_MIN)

    sigma = np.full(n_pixels, noise_sigma, dtype=float)
    if inject_window is not None:
        in_window = (wavelength >= inject_window.low) & (wavelength <= inject_window.high)
        sigma = np.where(in_window, noise_sigma * inject_excess_factor, sigma)

    noise = rng.normal(loc=0.0, scale=sigma)
    flux = continuum + noise
    ivar = 1.0 / (noise_sigma**2) * np.ones(n_pixels)  # pipeline-reported (uninflated) ivar

    and_mask = np.zeros(n_pixels, dtype=np.int64)
    or_mask = np.zeros(n_pixels, dtype=np.int64)
    sky = np.zeros(n_pixels, dtype=float)

    return Spectrum(
        source_id=source_id,
        wavelength=wavelength,
        flux=flux,
        ivar=ivar,
        and_mask=and_mask,
        or_mask=or_mask,
        sky=sky,
        obj_class=obj_class,
        subclass="",
        z=0.0,
        sn_median=float(continuum_level / noise_sigma),
    )


def make_synthetic_sample(
    n_spectra: int = 8,
    *,
    seed: int = 20260713,
    inject_window: Window | None = None,
    inject_excess_factor: float = 3.0,
) -> list[Spectrum]:
    """Deterministic sample of `n_spectra` synthetic spectra sharing one injected window."""
    spectra = []
    for i in range(n_spectra):
        spectra.append(
            make_synthetic_spectrum(
                seed=seed + i,
                source_id=f"SYNTH_{i:04d}",
                inject_window=inject_window,
                inject_excess_factor=inject_excess_factor,
            )
        )
    return spectra

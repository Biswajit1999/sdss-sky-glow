from __future__ import annotations

import numpy as np
import pytest

from sdss_sky_residual_quality_audit.continuum import evaluate_continuum, fit_local_continuum
from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.windows import Window


def _flat_spectrum(n=2000, level=20.0, seed=1):
    rng = np.random.default_rng(seed)
    wavelength = np.linspace(3900.0, 9100.0, n)
    flux = level + rng.normal(scale=0.01, size=n)
    ivar = np.full(n, 100.0)
    good = np.ones(n, dtype=bool)
    return wavelength, flux, ivar, good


def test_fit_recovers_flat_continuum():
    wavelength, flux, ivar, good = _flat_spectrum()
    window = Window("w", 5567.3, 5587.3)
    fit = fit_local_continuum(wavelength, flux, ivar, good, window, baseline_halfwidth=100.0, degree=1)
    predicted = evaluate_continuum(fit, np.array([window.center]))
    assert predicted[0] == pytest.approx(20.0, abs=0.1)


def test_fit_raises_on_insufficient_baseline_pixels():
    wavelength = np.array([5570.0, 5575.0, 5580.0])
    flux = np.array([20.0, 20.0, 20.0])
    ivar = np.array([100.0, 100.0, 100.0])
    good = np.ones(3, dtype=bool)
    window = Window("w", 5567.3, 5587.3)
    with pytest.raises(InsufficientDataError):
        fit_local_continuum(wavelength, flux, ivar, good, window, baseline_halfwidth=5.0, degree=1)


def test_fit_excludes_window_pixels_from_baseline():
    wavelength, flux, ivar, good = _flat_spectrum()
    window = Window("w", 5567.3, 5587.3)
    in_window = (wavelength >= window.low) & (wavelength <= window.high)
    flux = flux.copy()
    flux[in_window] += 1000.0  # huge spike inside the window only
    fit = fit_local_continuum(wavelength, flux, ivar, good, window, baseline_halfwidth=100.0, degree=1)
    predicted = evaluate_continuum(fit, np.array([window.center]))
    # continuum fit must not be dragged by the in-window spike
    assert predicted[0] == pytest.approx(20.0, abs=1.0)


def test_fit_respects_good_mask():
    wavelength, flux, ivar, good = _flat_spectrum()
    good = good.copy()
    good[:] = False
    window = Window("w", 5567.3, 5587.3)
    with pytest.raises(InsufficientDataError):
        fit_local_continuum(wavelength, flux, ivar, good, window)

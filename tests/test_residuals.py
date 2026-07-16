from __future__ import annotations

import numpy as np
import pytest

from sdss_sky_residual_quality_audit.continuum import fit_local_continuum
from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.residuals import (
    normalised_residuals,
    robust_std,
    window_residual_statistic,
)
from sdss_sky_residual_quality_audit.synthetic import make_synthetic_spectrum
from sdss_sky_residual_quality_audit.windows import SKY_WINDOW_PAIRS
from sdss_sky_residual_quality_audit.masks import good_pixel_mask


def test_robust_std_of_unit_normal_is_near_one():
    rng = np.random.default_rng(0)
    values = rng.normal(size=100000)
    assert robust_std(values) == pytest.approx(1.0, abs=0.05)


def test_robust_std_empty_is_nan():
    assert np.isnan(robust_std(np.array([])))


def test_injected_excess_window_has_larger_robust_std_than_control():
    pair = SKY_WINDOW_PAIRS[0]
    spectrum = make_synthetic_spectrum(
        source_id="SYNTH_INJECT", inject_window=pair.sky, inject_excess_factor=4.0
    )
    good = good_pixel_mask(spectrum.flux, spectrum.ivar, spectrum.and_mask)

    sky_fit = fit_local_continuum(spectrum.wavelength, spectrum.flux, spectrum.ivar, good, pair.sky)
    control_fit = fit_local_continuum(spectrum.wavelength, spectrum.flux, spectrum.ivar, good, pair.control)
    sky_resid = normalised_residuals(spectrum.wavelength, spectrum.flux, spectrum.ivar, good, sky_fit)
    control_resid = normalised_residuals(spectrum.wavelength, spectrum.flux, spectrum.ivar, good, control_fit)

    sky_stat = window_residual_statistic(spectrum.wavelength, sky_resid, pair.sky)
    control_stat = window_residual_statistic(spectrum.wavelength, control_resid, pair.control)

    assert sky_stat.robust_std > control_stat.robust_std
    # roughly the injected factor since ivar is the uninflated pipeline value
    assert sky_stat.robust_std / control_stat.robust_std > 2.0


def test_no_injection_gives_comparable_scales():
    pair = SKY_WINDOW_PAIRS[0]
    spectrum = make_synthetic_spectrum(source_id="SYNTH_NOINJECT", inject_window=None)
    good = good_pixel_mask(spectrum.flux, spectrum.ivar, spectrum.and_mask)

    sky_fit = fit_local_continuum(spectrum.wavelength, spectrum.flux, spectrum.ivar, good, pair.sky)
    control_fit = fit_local_continuum(spectrum.wavelength, spectrum.flux, spectrum.ivar, good, pair.control)
    sky_resid = normalised_residuals(spectrum.wavelength, spectrum.flux, spectrum.ivar, good, sky_fit)
    control_resid = normalised_residuals(spectrum.wavelength, spectrum.flux, spectrum.ivar, good, control_fit)

    sky_stat = window_residual_statistic(spectrum.wavelength, sky_resid, pair.sky)
    control_stat = window_residual_statistic(spectrum.wavelength, control_resid, pair.control)

    ratio = sky_stat.robust_std / control_stat.robust_std
    assert 0.5 < ratio < 2.0


def test_window_residual_statistic_raises_on_too_few_pixels():
    wavelength = np.array([5570.0, 5575.0])
    residual = np.array([0.1, 0.2])
    from sdss_sky_residual_quality_audit.windows import Window

    window = Window("w", 5567.3, 5587.3)
    with pytest.raises(InsufficientDataError):
        window_residual_statistic(wavelength, residual, window, min_pixels=5)

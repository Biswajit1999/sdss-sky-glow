from __future__ import annotations

import pytest

from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.masks import good_pixel_mask
from sdss_sky_residual_quality_audit.null_tests import (
    build_shifted_null_pair,
    evaluate_null_pair,
    summarise_null_test,
)
from sdss_sky_residual_quality_audit.synthetic import make_synthetic_sample
from sdss_sky_residual_quality_audit.windows import SKY_WINDOW_PAIRS


def test_build_shifted_null_pair_has_no_true_sky_line():
    pair = SKY_WINDOW_PAIRS[0]
    null_pair = build_shifted_null_pair(pair)
    assert null_pair.sky.low == pair.control.low
    assert null_pair.control.low != pair.control.low


def test_null_test_on_uninjected_synthetic_sample_passes():
    pair = SKY_WINDOW_PAIRS[0]
    null_pair = build_shifted_null_pair(pair)
    spectra = make_synthetic_sample(n_spectra=12, inject_window=None)

    excesses = []
    for spectrum in spectra:
        good = good_pixel_mask(spectrum.flux, spectrum.ivar, spectrum.and_mask)
        excesses.append(
            evaluate_null_pair(
                spectrum.source_id, spectrum.wavelength, spectrum.flux, spectrum.ivar, good, null_pair
            )
        )
    summary = summarise_null_test(excesses)
    assert summary.passed
    assert summary.n_spectra == 12


def test_summarise_null_test_raises_on_empty():
    with pytest.raises(InsufficientDataError):
        summarise_null_test([])

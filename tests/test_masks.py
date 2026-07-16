from __future__ import annotations

import numpy as np

from sdss_sky_residual_quality_audit.masks import (
    HARD_EXCLUDE_BITS,
    SKY_QUALITY_BITS,
    good_pixel_mask,
    sky_quality_flag_mask,
)


def test_good_pixel_mask_excludes_nonfinite_flux():
    flux = np.array([1.0, np.nan, 2.0])
    ivar = np.array([1.0, 1.0, 1.0])
    and_mask = np.zeros(3, dtype=np.int64)
    mask = good_pixel_mask(flux, ivar, and_mask)
    assert mask.tolist() == [True, False, True]


def test_good_pixel_mask_excludes_nonpositive_ivar():
    flux = np.array([1.0, 2.0, 3.0])
    ivar = np.array([1.0, 0.0, -1.0])
    and_mask = np.zeros(3, dtype=np.int64)
    mask = good_pixel_mask(flux, ivar, and_mask)
    assert mask.tolist() == [True, False, False]


def test_good_pixel_mask_excludes_hard_bits():
    flux = np.array([1.0, 2.0])
    ivar = np.array([1.0, 1.0])
    and_mask = np.array([1 << HARD_EXCLUDE_BITS[0], 0], dtype=np.int64)
    mask = good_pixel_mask(flux, ivar, and_mask)
    assert mask.tolist() == [False, True]


def test_good_pixel_mask_does_not_exclude_sky_quality_bits_by_default():
    flux = np.array([1.0])
    ivar = np.array([1.0])
    and_mask = np.array([1 << SKY_QUALITY_BITS[0]], dtype=np.int64)
    mask = good_pixel_mask(flux, ivar, and_mask)
    assert mask.tolist() == [True]


def test_good_pixel_mask_excludes_sky_quality_bits_when_requested():
    flux = np.array([1.0])
    ivar = np.array([1.0])
    and_mask = np.array([1 << SKY_QUALITY_BITS[0]], dtype=np.int64)
    mask = good_pixel_mask(flux, ivar, and_mask, extra_exclude_bits=SKY_QUALITY_BITS)
    assert mask.tolist() == [False]


def test_sky_quality_flag_mask_detects_bits():
    and_mask = np.array([1 << SKY_QUALITY_BITS[0], 0], dtype=np.int64)
    flagged = sky_quality_flag_mask(and_mask)
    assert flagged.tolist() == [True, False]

"""Shared synthetic-data fixtures for tests.

The synthetic-data model lives in
`sdss_sky_residual_quality_audit.synthetic` (shared with
`scripts/run_analysis.py --demo`); this module only adds the pytest fixture
layer on top.
"""
from __future__ import annotations

import pytest

from sdss_sky_residual_quality_audit.synthetic import make_synthetic_sample, make_synthetic_spectrum
from sdss_sky_residual_quality_audit.windows import SKY_WINDOW_PAIRS

INJECT_PAIR = SKY_WINDOW_PAIRS[0]  # OI_5577


@pytest.fixture
def synthetic_spectrum():
    return make_synthetic_spectrum(source_id="SYNTH_TEST_0000")


@pytest.fixture
def synthetic_spectrum_with_injection():
    return make_synthetic_spectrum(
        source_id="SYNTH_TEST_INJECT",
        inject_window=INJECT_PAIR.sky,
        inject_excess_factor=4.0,
    )


@pytest.fixture
def synthetic_sample_no_injection():
    return make_synthetic_sample(n_spectra=10, inject_window=None)


@pytest.fixture
def synthetic_sample_with_injection():
    return make_synthetic_sample(
        n_spectra=10, inject_window=INJECT_PAIR.sky, inject_excess_factor=4.0
    )

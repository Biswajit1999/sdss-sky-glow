from __future__ import annotations

from sdss_sky_residual_quality_audit.synthetic import make_synthetic_sample, make_synthetic_spectrum


def test_synthetic_spectrum_is_deterministic():
    s1 = make_synthetic_spectrum(seed=7)
    s2 = make_synthetic_spectrum(seed=7)
    assert (s1.flux == s2.flux).all()


def test_synthetic_spectrum_labelled_as_synthetic():
    spectrum = make_synthetic_spectrum()
    assert spectrum.source_id.startswith("SYNTH_")


def test_synthetic_sample_has_distinct_ids():
    sample = make_synthetic_sample(n_spectra=5)
    ids = {s.source_id for s in sample}
    assert len(ids) == 5


def test_synthetic_spectrum_wavelength_covers_sdss_range():
    spectrum = make_synthetic_spectrum()
    assert spectrum.wavelength.min() <= 4000.0
    assert spectrum.wavelength.max() >= 9000.0

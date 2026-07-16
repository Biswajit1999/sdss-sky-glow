from __future__ import annotations

import numpy as np
import pytest
from astropy.io import fits

from sdss_sky_residual_quality_audit.exceptions import DataSchemaError
from sdss_sky_residual_quality_audit.io import load_spectrum_file, load_spectrum_hdulist


def _make_coadd_hdulist(n=100, missing_col=None):
    loglam = np.linspace(3.6, 3.9, n)
    flux = np.full(n, 20.0)
    ivar = np.full(n, 100.0)
    and_mask = np.zeros(n, dtype=np.int32)
    or_mask = np.zeros(n, dtype=np.int32)
    cols = [
        fits.Column(name="flux", format="E", array=flux),
        fits.Column(name="loglam", format="E", array=loglam),
        fits.Column(name="ivar", format="E", array=ivar),
        fits.Column(name="and_mask", format="J", array=and_mask),
        fits.Column(name="or_mask", format="J", array=or_mask),
        fits.Column(name="sky", format="E", array=np.zeros(n)),
    ]
    if missing_col:
        cols = [c for c in cols if c.name != missing_col]
    coadd_hdu = fits.BinTableHDU.from_columns(cols, name="COADD")
    primary = fits.PrimaryHDU()
    return fits.HDUList([primary, coadd_hdu])


def test_load_spectrum_hdulist_parses_wavelength_and_flux():
    hdul = _make_coadd_hdulist()
    spectrum = load_spectrum_hdulist(hdul, "TEST_0001")
    assert spectrum.source_id == "TEST_0001"
    assert spectrum.wavelength.size == 100
    assert np.allclose(spectrum.wavelength, 10.0 ** hdul[1].data["loglam"])
    assert spectrum.obj_class == "UNKNOWN"


def test_load_spectrum_hdulist_raises_on_missing_hdu():
    hdul = fits.HDUList([fits.PrimaryHDU()])
    with pytest.raises(DataSchemaError):
        load_spectrum_hdulist(hdul, "TEST")


def test_load_spectrum_hdulist_raises_on_missing_column():
    hdul = _make_coadd_hdulist(missing_col="ivar")
    with pytest.raises(DataSchemaError):
        load_spectrum_hdulist(hdul, "TEST")


def test_load_spectrum_file_raises_on_missing_path(tmp_path):
    with pytest.raises(DataSchemaError):
        load_spectrum_file(tmp_path / "does_not_exist.fits")


def test_load_spectrum_file_roundtrip(tmp_path):
    hdul = _make_coadd_hdulist()
    path = tmp_path / "spec-test.fits"
    hdul.writeto(path)
    spectrum = load_spectrum_file(path)
    assert spectrum.wavelength.size == 100

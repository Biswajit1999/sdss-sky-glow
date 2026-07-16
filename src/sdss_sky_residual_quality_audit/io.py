"""Load SDSS/BOSS `spec-*.fits` coadd spectra into a typed `Spectrum`.

FITS structure verified live against the official SDSS DR17 spec datamodel
(https://data.sdss.org/datamodel/files/BOSS_SPECTRO_REDUX/RUN2D/spectra/full/PLATE4/spec.html,
see IMPLEMENTATION_PLAN.md sec.2 item 6): HDU0 primary header, HDU1 'COADD'
binary table (flux, loglam, ivar, and_mask, or_mask, wdisp, sky, model), HDU2
'SPALL' one-row summary table (class, subclass, z, zWarning, snMedian, ...).
Wavelengths in `loglam` are vacuum wavelengths (verified against
https://www.sdss4.org/dr17/spectro/spectro_basics/), so `wavelength = 10**loglam`
is already the vacuum Angstrom wavelength used throughout this project.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from astropy.io import fits

from sdss_sky_residual_quality_audit.exceptions import DataSchemaError

_REQUIRED_COADD_COLUMNS = ("flux", "loglam", "ivar", "and_mask", "or_mask")


@dataclass(frozen=True)
class Spectrum:
    """A single SDSS coadded spectrum with the fields this project needs.

    `wavelength` is vacuum Angstroms; `flux`/`sky` are in units of
    1e-17 erg/s/cm^2/Angstrom (per the datamodel); `ivar` is the inverse
    variance of `flux` in the same units.
    """

    source_id: str
    wavelength: np.ndarray
    flux: np.ndarray
    ivar: np.ndarray
    and_mask: np.ndarray
    or_mask: np.ndarray
    sky: np.ndarray | None
    obj_class: str
    subclass: str
    z: float
    sn_median: float


def _first_present(names: tuple[str, ...], available: set[str]) -> str | None:
    for name in names:
        if name in available:
            return name
    return None


def load_spectrum_hdulist(hdul: fits.HDUList, source_id: str) -> Spectrum:
    """Parse an already-open SDSS `spec` HDUList into a `Spectrum`.

    Raises `DataSchemaError` (never a bare `KeyError`/`IndexError`) if the
    expected HDU1 COADD table or its required columns are absent, or if
    array lengths within the table are inconsistent.
    """
    if len(hdul) < 2:
        raise DataSchemaError(
            f"{source_id}: expected >=2 HDUs (primary + COADD), found {len(hdul)}"
        )

    coadd = hdul[1]
    if not hasattr(coadd, "columns") or coadd.data is None:
        raise DataSchemaError(f"{source_id}: HDU1 is not a binary table (expected COADD)")

    available = {c.lower() for c in coadd.columns.names}
    missing = [c for c in _REQUIRED_COADD_COLUMNS if c not in available]
    if missing:
        raise DataSchemaError(f"{source_id}: COADD table missing required columns {missing}")

    # Column name casing is not guaranteed identical to the datamodel; look up
    # case-insensitively rather than assuming lower-case (same defensive
    # pattern used for the Gaia archive in the euclid sibling project).
    colmap = {c.lower(): c for c in coadd.columns.names}
    data = coadd.data

    loglam = np.asarray(data[colmap["loglam"]], dtype=float)
    flux = np.asarray(data[colmap["flux"]], dtype=float)
    ivar = np.asarray(data[colmap["ivar"]], dtype=float)
    and_mask = np.asarray(data[colmap["and_mask"]], dtype=np.int64)
    or_mask = np.asarray(data[colmap["or_mask"]], dtype=np.int64)

    lengths = {loglam.size, flux.size, ivar.size, and_mask.size, or_mask.size}
    if len(lengths) != 1:
        raise DataSchemaError(f"{source_id}: COADD columns have inconsistent lengths {lengths}")
    if loglam.size == 0:
        raise DataSchemaError(f"{source_id}: COADD table is empty")

    sky = None
    sky_col = _first_present(("sky",), available)
    if sky_col is not None:
        sky_arr = np.asarray(data[colmap[sky_col]], dtype=float)
        if sky_arr.size == loglam.size:
            sky = sky_arr

    wavelength = 10.0**loglam

    obj_class, subclass, z, sn_median = "UNKNOWN", "", float("nan"), float("nan")
    if len(hdul) >= 3 and getattr(hdul[2], "data", None) is not None and len(hdul[2].data) > 0:
        spall = hdul[2].data
        spall_cols = {c.lower(): c for c in spall.columns.names}
        row = spall[0]

        def _get_str(*names: str) -> str:
            col = _first_present(names, set(spall_cols))
            if col is None:
                return ""
            value = row[spall_cols[col]]
            return str(value).strip()

        def _get_float(*names: str) -> float:
            col = _first_present(names, set(spall_cols))
            if col is None:
                return float("nan")
            try:
                return float(row[spall_cols[col]])
            except (TypeError, ValueError):
                return float("nan")

        obj_class = _get_str("class") or "UNKNOWN"
        subclass = _get_str("subclass")
        z = _get_float("z")
        sn_median = _get_float("sn_median", "snmedian")

    return Spectrum(
        source_id=source_id,
        wavelength=wavelength,
        flux=flux,
        ivar=ivar,
        and_mask=and_mask,
        or_mask=or_mask,
        sky=sky,
        obj_class=obj_class,
        subclass=subclass,
        z=z,
        sn_median=sn_median,
    )


def load_spectrum_file(path: str | Path, source_id: str | None = None) -> Spectrum:
    """Load a `spec-*.fits` file from disk into a `Spectrum`."""
    file_path = Path(path)
    if not file_path.is_file():
        raise DataSchemaError(f"spectrum file not found: {file_path}")
    sid = source_id or file_path.stem
    try:
        with fits.open(file_path, memmap=False) as hdul:
            return load_spectrum_hdulist(hdul, sid)
    except OSError as exc:
        raise DataSchemaError(f"{sid}: could not open FITS file {file_path}: {exc}") from exc

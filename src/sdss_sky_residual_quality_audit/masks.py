"""SDSS SPPIXMASK bit definitions and pixel-selection masks.

Bit table verified live against the official SDSS DR17 bitmask documentation,
https://www.sdss4.org/dr17/algorithms/bitmasks/#SPPIXMASK (see
IMPLEMENTATION_PLAN.md sec.2 item 5). `AND_MASK`/`OR_MASK` in the COADD table
use these same SPPIXMASK bit definitions.

Design choice central to this project's scientific question: the four
sky-residual-quality bits (`NOSKY`, `BRIGHTSKY`, `BADSKYCHI`, `REDMONSTER`)
are the pipeline's own signal of exactly the phenomenon under study here, so
`good_pixel_mask` does **not** exclude them by default -- excluding them would
remove the signal we are trying to measure. They are instead surfaced
separately via `sky_quality_flag_mask` for the mask-sensitivity validation
check (docs/VALIDATION_CONTRACT.md): rerunning the analysis with those bits
also excluded and comparing the resulting excess statistic.
"""
from __future__ import annotations

import numpy as np

# Full 32-bit SPPIXMASK table (bit -> (name, description)); bits 13-15 and
# 29-31 are unused/reserved in the source documentation.
SPPIXMASK_BITS: dict[int, tuple[str, str]] = {
    0: ("NOPLUG", "Fiber not listed in plugmap file"),
    1: ("BADTRACE", "Bad trace from routine TRACE320CRUDE"),
    2: ("BADFLAT", "Low counts in fiberflat"),
    3: ("BADARC", "Bad arc solution"),
    4: ("MANYBADCOLUMNS", "More than 10% of pixels are bad columns"),
    5: ("MANYREJECTED", "More than 10% of pixels are rejected in extraction"),
    6: ("LARGESHIFT", "Large spatial shift between flat and object position"),
    7: ("BADSKYFIBER", "Sky fiber shows extreme residuals"),
    8: ("NEARWHOPPER", "DEPRECATED, no longer set as of BOSS DR9"),
    9: ("WHOPPER", "Whopping fiber, with a very bright source"),
    10: ("SMEARIMAGE", "DEPRECATED. Prior to DR9 meant smear available for red and blue cameras"),
    11: ("SMEARHIGHSN", "DEPRECATED. Prior to DR9 meant S/N sufficient for full smear fit"),
    12: ("SMEARMEDSN", "DEPRECATED. Prior to DR9 meant S/N only sufficient for scaled median fit"),
    16: ("NEARBADPIXEL", "Bad pixel within 3 pixels of trace"),
    17: ("LOWFLAT", "Flat field less than 0.5"),
    18: ("FULLREJECT", "Pixel fully rejected in extraction (INVVAR=0)"),
    19: ("PARTIALREJECT", "Some pixels rejected in extraction"),
    20: ("SCATTEREDLIGHT", "Scattered light significant"),
    21: ("CROSSTALK", "Cross-talk significant"),
    22: ("NOSKY", "Sky level unknown at this wavelength (INVVAR=0)"),
    23: ("BRIGHTSKY", "Sky level > flux + 10*(flux_err) AND sky > 1.25 * median(sky,99 pixels)"),
    24: ("NODATA", "DEPRECATED, should be ignored in favor of flagging on INVVAR=0"),
    25: ("COMBINEREJ", "Rejected in combine B-spline"),
    26: ("BADFLUXFACTOR", "Low flux-calibration or flux-correction factor"),
    27: ("BADSKYCHI", "Relative chi^2 > 3 in sky residuals at this wavelength"),
    28: ("REDMONSTER", "Contiguous region of bad chi^2 in sky residuals (threshold chi^2 > 3)"),
}

# Bits that indicate a genuinely unusable pixel for *any* science purpose,
# unrelated to the sky-residual phenomenon under study; always excluded.
HARD_EXCLUDE_BITS: tuple[int, ...] = (
    0, 1, 2, 3, 4, 5, 6, 16, 17, 18, 19, 20, 21, 24, 25, 26,
)

# The pipeline's own sky-subtraction-quality flags -- deliberately not part
# of HARD_EXCLUDE_BITS (see module docstring); used for the mask-sensitivity
# validation check instead.
SKY_QUALITY_BITS: tuple[int, ...] = (22, 23, 27, 28)


def _bitmask_flag(mask: np.ndarray, bits: tuple[int, ...]) -> np.ndarray:
    combined = 0
    for bit in bits:
        combined |= 1 << bit
    return (np.asarray(mask, dtype=np.int64) & combined) != 0


def good_pixel_mask(
    flux: np.ndarray,
    ivar: np.ndarray,
    and_mask: np.ndarray,
    *,
    extra_exclude_bits: tuple[int, ...] = (),
) -> np.ndarray:
    """Boolean array, True where a pixel is usable for this analysis.

    Excludes non-finite flux, non-positive/non-finite ivar, and any
    `HARD_EXCLUDE_BITS` (plus caller-supplied `extra_exclude_bits`, used by
    the mask-sensitivity check to additionally exclude `SKY_QUALITY_BITS`).
    Sky-quality bits are NOT excluded by default.
    """
    flux = np.asarray(flux, dtype=float)
    ivar = np.asarray(ivar, dtype=float)
    finite = np.isfinite(flux) & np.isfinite(ivar)
    positive_ivar = ivar > 0
    bits = HARD_EXCLUDE_BITS + tuple(extra_exclude_bits)
    not_flagged = ~_bitmask_flag(and_mask, bits)
    return finite & positive_ivar & not_flagged


def sky_quality_flag_mask(and_mask: np.ndarray) -> np.ndarray:
    """Boolean array, True where any SKY_QUALITY_BITS bit is set in AND_MASK."""
    return _bitmask_flag(and_mask, SKY_QUALITY_BITS)

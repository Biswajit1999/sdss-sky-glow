"""Night-sky emission-line windows and matched local control windows.

Wavelengths are the standard, widely-documented rest-frame wavelengths of the
brightest optical/near-IR night-sky (airglow) emission features:

- [OI] 5577.3 A (auroral green line) and [OI] 6300.3/6363.8 A (auroral red
  doublet): the SDSS DR17 bitmask documentation itself names 5577 A directly
  as a wavelength where pipeline error estimates "can be untrustworthy"
  (https://www.sdss4.org/dr17/algorithms/bitmasks/#SPPIXMASK, verified live --
  see IMPLEMENTATION_PLAN.md sec.2 item 5), i.e. a documented, not invented,
  problem wavelength.
- Na D sky emission (mesospheric sodium layer, ~5890/5896 A).
- The OH Meinel-band airglow forest, strong redward of ~7200 A.

These are standard values covered by the flux-calibrated optical/near-IR
night-sky atlas of Hanuschik (2003, A&A 407, 1157; DOI
10.1051/0004-6361:20030885, verified via the CrossRef API -- see
IMPLEMENTATION_PLAN.md sec.2 item 7), which spans the full SDSS/BOSS optical
range (3140-10430 A vs. SDSS's 3800-10400 A) and is the standard reference
atlas for these auroral and airglow features; individual line-centre values
here are not re-derived from that atlas but are the commonly quoted round
values for these well-known features (documented in
docs/ASSUMPTIONS_AND_LIMITATIONS.md rather than claimed as atlas-precision
measurements).

Each sky window is paired with an adjacent "local control" window of the same
width, offset in wavelength but close enough to sample essentially the same
local continuum and instrumental response.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    name: str
    low: float
    high: float

    def __post_init__(self) -> None:
        if not (self.low < self.high):
            raise ValueError(f"window '{self.name}': low ({self.low}) must be < high ({self.high})")

    @property
    def center(self) -> float:
        return 0.5 * (self.low + self.high)

    @property
    def width(self) -> float:
        return self.high - self.low

    def shifted(self, delta: float, suffix: str = "_shifted") -> "Window":
        return Window(name=f"{self.name}{suffix}", low=self.low + delta, high=self.high + delta)


@dataclass(frozen=True)
class WindowPair:
    label: str
    sky: Window
    control: Window
    citation_note: str


# Hardcoded, deterministic, documented sky/control window pairs. Widths and
# offsets are chosen so that: (a) each sky window fully contains its named
# line's documented wavelength with margin, (b) each control window is
# adjacent (small gap) so it samples the same local continuum, and (c) no
# window overlaps another sky window in this table.
SKY_WINDOW_PAIRS: tuple[WindowPair, ...] = (
    WindowPair(
        label="OI_5577",
        sky=Window("OI_5577_sky", 5567.3, 5587.3),
        control=Window("OI_5577_control", 5537.3, 5557.3),
        citation_note="[OI] 5577.3A auroral line; SDSS DR17 bitmask docs name 5577A directly.",
    ),
    WindowPair(
        label="NaD_5890",
        sky=Window("NaD_5890_sky", 5880.0, 5905.0),
        control=Window("NaD_5890_control", 5850.0, 5875.0),
        citation_note="Na D mesospheric sky emission doublet, ~5889.95/5895.92A.",
    ),
    WindowPair(
        label="OI_6300",
        sky=Window("OI_6300_sky", 6290.0, 6310.0),
        control=Window("OI_6300_control", 6315.0, 6335.0),
        citation_note="[OI] 6300.3A auroral red-doublet component.",
    ),
    WindowPair(
        label="OI_6364",
        sky=Window("OI_6364_sky", 6353.8, 6373.8),
        control=Window("OI_6364_control", 6378.8, 6398.8),
        citation_note="[OI] 6363.8A auroral red-doublet component.",
    ),
    WindowPair(
        label="OH_forest_7600",
        sky=Window("OH_forest_7600_sky", 7550.0, 7700.0),
        control=Window("OH_forest_7600_control", 7350.0, 7500.0),
        citation_note="Onset of the strong OH Meinel-band airglow forest, red of ~7200A.",
    ),
)


def window_within_range(window: Window, wavelength_min: float, wavelength_max: float, margin: float = 5.0) -> bool:
    """True if `window` lies fully within [wavelength_min, wavelength_max] with `margin` to spare."""
    return (window.low - margin) >= wavelength_min and (window.high + margin) <= wavelength_max


def pair_within_range(pair: WindowPair, wavelength_min: float, wavelength_max: float, margin: float = 5.0) -> bool:
    return window_within_range(pair.sky, wavelength_min, wavelength_max, margin) and window_within_range(
        pair.control, wavelength_min, wavelength_max, margin
    )

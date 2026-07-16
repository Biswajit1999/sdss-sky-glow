"""Per-spectrum and cross-spectrum sky-vs-control excess statistics.

For each `WindowPair` (sky window + matched local control window) and each
spectrum, defines an excess statistic comparing the residual scale inside
the sky window to the residual scale inside its matched control window:
`ratio = sky_robust_std / control_robust_std` and `difference = sky_robust_std
- control_robust_std`. Values > 1 / > 0 indicate elevated residual structure
in the sky window relative to the control.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.residuals import WindowResiduals


@dataclass(frozen=True)
class PairExcess:
    label: str
    source_id: str
    sky_robust_std: float
    control_robust_std: float
    ratio: float
    difference: float
    sky_n_pixels: int
    control_n_pixels: int


def pair_excess_statistic(
    label: str,
    source_id: str,
    sky: WindowResiduals,
    control: WindowResiduals,
) -> PairExcess:
    """Compute the sky-vs-control excess statistic for one window pair, one spectrum."""
    if control.robust_std <= 0 or not np.isfinite(control.robust_std):
        raise InsufficientDataError(
            f"{source_id}/{label}: control window robust_std is non-positive or non-finite, "
            "cannot form a ratio"
        )
    ratio = float(sky.robust_std / control.robust_std)
    difference = float(sky.robust_std - control.robust_std)
    return PairExcess(
        label=label,
        source_id=source_id,
        sky_robust_std=sky.robust_std,
        control_robust_std=control.robust_std,
        ratio=ratio,
        difference=difference,
        sky_n_pixels=sky.n_pixels,
        control_n_pixels=control.n_pixels,
    )


@dataclass(frozen=True)
class AggregateExcess:
    label: str
    n_spectra: int
    median_ratio: float
    median_difference: float


def aggregate_excess(label: str, excesses: list[PairExcess]) -> AggregateExcess:
    """Aggregate per-spectrum `PairExcess` values (for one window-pair label) across spectra."""
    matching = [e for e in excesses if e.label == label]
    if not matching:
        raise InsufficientDataError(f"no PairExcess entries found for label '{label}'")
    ratios = np.array([e.ratio for e in matching], dtype=float)
    diffs = np.array([e.difference for e in matching], dtype=float)
    return AggregateExcess(
        label=label,
        n_spectra=len(matching),
        median_ratio=float(np.median(ratios)),
        median_difference=float(np.median(diffs)),
    )


def stratify_by_class(
    excesses: list[PairExcess], classes: dict[str, str]
) -> dict[str, list[PairExcess]]:
    """Group `PairExcess` entries by `classes[source_id]` (e.g. SDSS object class)."""
    groups: dict[str, list[PairExcess]] = {}
    for e in excesses:
        key = classes.get(e.source_id, "UNKNOWN")
        groups.setdefault(key, []).append(e)
    return groups


def stratify_by_snr(
    excesses: list[PairExcess],
    snr: dict[str, float],
    *,
    bins: tuple[float, ...] = (0.0, 5.0, 15.0, float("inf")),
    labels: tuple[str, ...] = ("low_snr", "mid_snr", "high_snr"),
) -> dict[str, list[PairExcess]]:
    """Group `PairExcess` entries into SNR bins using `snr[source_id]` (e.g. snMedian)."""
    if len(labels) != len(bins) - 1:
        raise InsufficientDataError("stratify_by_snr: labels must have len(bins) - 1 entries")
    groups: dict[str, list[PairExcess]] = {label: [] for label in labels}
    for e in excesses:
        value = snr.get(e.source_id, float("nan"))
        if not np.isfinite(value):
            continue
        for lo, hi, label in zip(bins[:-1], bins[1:], labels):
            if lo <= value < hi:
                groups[label].append(e)
                break
    return groups

from __future__ import annotations

import pytest

from sdss_sky_residual_quality_audit.exceptions import InsufficientDataError
from sdss_sky_residual_quality_audit.metrics import (
    PairExcess,
    aggregate_excess,
    pair_excess_statistic,
    stratify_by_class,
    stratify_by_snr,
)
from sdss_sky_residual_quality_audit.residuals import WindowResiduals


def _wr(name, std, n=10):
    return WindowResiduals(window_name=name, residuals=None, n_pixels=n, robust_std=std, rms=std)


def test_pair_excess_statistic_ratio_and_difference():
    sky = _wr("sky", 2.0)
    control = _wr("control", 1.0)
    excess = pair_excess_statistic("label", "SRC1", sky, control)
    assert excess.ratio == pytest.approx(2.0)
    assert excess.difference == pytest.approx(1.0)


def test_pair_excess_statistic_raises_on_zero_control_std():
    sky = _wr("sky", 2.0)
    control = _wr("control", 0.0)
    with pytest.raises(InsufficientDataError):
        pair_excess_statistic("label", "SRC1", sky, control)


def test_aggregate_excess_median():
    excesses = [
        PairExcess("L", "S1", 2.0, 1.0, 2.0, 1.0, 10, 10),
        PairExcess("L", "S2", 3.0, 1.0, 3.0, 2.0, 10, 10),
        PairExcess("L", "S3", 4.0, 1.0, 4.0, 3.0, 10, 10),
    ]
    agg = aggregate_excess("L", excesses)
    assert agg.n_spectra == 3
    assert agg.median_ratio == pytest.approx(3.0)


def test_aggregate_excess_raises_when_no_match():
    with pytest.raises(InsufficientDataError):
        aggregate_excess("MISSING", [])


def test_stratify_by_class():
    excesses = [
        PairExcess("L", "S1", 2.0, 1.0, 2.0, 1.0, 10, 10),
        PairExcess("L", "S2", 3.0, 1.0, 3.0, 2.0, 10, 10),
    ]
    classes = {"S1": "GALAXY", "S2": "STAR"}
    groups = stratify_by_class(excesses, classes)
    assert set(groups.keys()) == {"GALAXY", "STAR"}


def test_stratify_by_snr_bins():
    excesses = [
        PairExcess("L", "S1", 2.0, 1.0, 2.0, 1.0, 10, 10),
        PairExcess("L", "S2", 3.0, 1.0, 3.0, 2.0, 10, 10),
    ]
    snr = {"S1": 2.0, "S2": 20.0}
    groups = stratify_by_snr(excesses, snr)
    assert groups["low_snr"][0].source_id == "S1"
    assert groups["high_snr"][0].source_id == "S2"

from __future__ import annotations

import pytest

from sdss_sky_residual_quality_audit.windows import (
    SKY_WINDOW_PAIRS,
    Window,
    pair_within_range,
    window_within_range,
)


def test_window_rejects_inverted_bounds():
    with pytest.raises(ValueError):
        Window("bad", 100.0, 50.0)


def test_window_center_and_width():
    w = Window("x", 100.0, 120.0)
    assert w.center == 110.0
    assert w.width == 20.0


def test_window_shifted():
    w = Window("x", 100.0, 120.0)
    shifted = w.shifted(50.0)
    assert shifted.low == 150.0
    assert shifted.high == 170.0
    assert shifted.name == "x_shifted"


def test_all_sky_pairs_non_overlapping_and_valid():
    for pair in SKY_WINDOW_PAIRS:
        assert pair.sky.low < pair.sky.high
        assert pair.control.low < pair.control.high


def test_window_within_range():
    w = Window("x", 5000.0, 5010.0)
    assert window_within_range(w, 3800.0, 9200.0)
    assert not window_within_range(w, 5005.0, 9200.0)


def test_pair_within_range_sdss_optical_coverage():
    for pair in SKY_WINDOW_PAIRS:
        assert pair_within_range(pair, 3800.0, 9200.0)

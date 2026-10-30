"""Spectrum-paired robustness diagnostics for SDSS sky/control residual ratios.

Inputs are positive sky/control residual-scale ratios, one row per spectrum.
All resampling is at the *spectrum* level. Synthetic examples are not DR17
observations or replacements for the repository's existing residual pipeline.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _log_matrix(ratios: np.ndarray) -> np.ndarray:
    arr = np.asarray(ratios, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 3 or arr.shape[1] < 1:
        raise ValueError("ratios must be a 2D array with >=3 spectra and >=1 window")
    if np.any(np.isinf(arr)) or np.any((arr <= 0) & ~np.isnan(arr)):
        raise ValueError("finite ratios must be strictly positive; missing values may be NaN")
    logs = np.log(arr)
    if np.any(np.sum(np.isfinite(logs), axis=0) < 3):
        raise ValueError("each window needs at least three observed spectra")
    return logs


def paired_bootstrap(ratios: np.ndarray, *, seed: int = 20261030,
                     n_resamples: int = 2000, confidence: float = 0.95) -> dict[str, np.ndarray]:
    """Median log-ratio intervals with common resampled spectrum IDs across windows.

    Row resampling retains observed cross-window dependence and missingness.
    It does not correct shared-plate or calibration systematics.
    """
    logs = _log_matrix(ratios)
    if not isinstance(n_resamples, int) or n_resamples < 100:
        raise ValueError("n_resamples must be >=100")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie strictly between zero and one")
    rng = np.random.default_rng(seed)
    n, k = logs.shape
    draws = np.empty((n_resamples, k))
    for b in range(n_resamples):
        sampled = logs[rng.integers(0, n, size=n)]
        for j in range(k):
            valid = sampled[np.isfinite(sampled[:, j]), j]
            draws[b, j] = np.median(valid) if valid.size else np.nan
    alpha = (1 - confidence) / 2
    point = np.nanmedian(logs, axis=0)
    lower = np.nanquantile(draws, alpha, axis=0)
    upper = np.nanquantile(draws, 1 - alpha, axis=0)
    return {"median_log_ratio": point, "median_ratio": np.exp(point),
            "lower_ratio": np.exp(lower), "upper_ratio": np.exp(upper),
            "draws_log": draws}


def leave_one_spectrum_out(ratios: np.ndarray) -> dict[str, np.ndarray]:
    """Influence of deleting each complete spectrum row on median log excess."""
    logs = _log_matrix(ratios)
    n, k = logs.shape
    full = np.nanmedian(logs, axis=0)
    leave = np.full((n, k), np.nan)
    for i in range(n):
        sub = np.delete(logs, i, axis=0)
        for j in range(k):
            col = sub[np.isfinite(sub[:, j]), j]
            if col.size >= 2:
                leave[i, j] = np.median(col)
    delta = leave - full
    return {"full_log_median": full, "leave_one_out_log_median": leave,
            "delta_log": delta, "max_abs_delta_log": np.nanmax(np.abs(delta), axis=0)}


def sign_flip_pvalues(ratios: np.ndarray, *, seed: int = 20261030,
                      n_resamples: int = 20000) -> np.ndarray:
    """Two-sided sign-flip test of mean log ratio=0 for each window.

    Exact enumeration for <=16 observed spectra; seeded Monte Carlo otherwise.
    Validity requires independent, sign-exchangeable spectrum-level log ratios
    under the null; the same-plate data may violate that assumption.
    """
    logs = _log_matrix(ratios)
    if not isinstance(n_resamples, int) or n_resamples < 100:
        raise ValueError("n_resamples must be >=100")
    rng = np.random.default_rng(seed)
    pvalues = []
    for j in range(logs.shape[1]):
        x = logs[np.isfinite(logs[:, j]), j]
        n = x.size
        observed = abs(float(np.mean(x)))
        if n <= 16:
            integers = np.arange(1 << n, dtype=np.uint32)
            bits = (integers[:, None] >> np.arange(n, dtype=np.uint32)) & 1
            signs = 2 * bits.astype(np.int8) - 1
            simulated = np.abs(signs @ x / n)
            p = float(np.mean(simulated >= observed - 1e-12))
        else:
            signs = rng.choice(np.array([-1, 1], dtype=np.int8), size=(n_resamples, n))
            simulated = np.abs(signs @ x / n)
            p = float((1 + np.count_nonzero(simulated >= observed - 1e-12)) /
                      (n_resamples + 1))
        pvalues.append(p)
    return np.asarray(pvalues)


def holm_adjust(pvalues: np.ndarray) -> np.ndarray:
    """Familywise Holm step-down adjusted p-values for a predeclared window set."""
    p = np.asarray(pvalues, dtype=float)
    if p.ndim != 1 or p.size == 0 or np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("pvalues must be a finite 1D vector within [0, 1]")
    idx = np.argsort(p, kind="stable")
    adjusted_sorted = np.maximum.accumulate((p.size - np.arange(p.size)) * p[idx])
    result = np.empty_like(p)
    result[idx] = np.minimum(1.0, adjusted_sorted)
    return result


def diagnostic_report() -> dict[str, object]:
    """Seeded, correlated synthetic residual ratios; never archive data."""
    rng = np.random.default_rng(3040)
    n = 40
    common = rng.normal(0, 0.09, (n, 1))
    independent = rng.normal(0, 0.12, (n, 5))
    injected = np.array([0.38, 0.45, 0.0, 0.0, 0.0])
    ratios = np.exp(common + independent + injected)
    bootstrap = paired_bootstrap(ratios, seed=3040, n_resamples=2000)
    influence = leave_one_spectrum_out(ratios)
    raw_p = sign_flip_pvalues(ratios, seed=3040, n_resamples=20000)
    return {
        "input": "synthetic positive residual-scale ratios, not SDSS spectra",
        "seed": 3040, "n_spectra": n,
        "labels": ["OI_5577", "OI_6300", "NaD_5890", "OI_6364", "OH_forest_7600"],
        "injected_log_ratio": injected.tolist(),
        "median_ratio": bootstrap["median_ratio"].tolist(),
        "bootstrap_95_ratio_interval": list(zip(
            bootstrap["lower_ratio"].tolist(), bootstrap["upper_ratio"].tolist())),
        "max_loo_delta_log": influence["max_abs_delta_log"].tolist(),
        "raw_signflip_p": raw_p.tolist(), "holm_adjusted_p": holm_adjust(raw_p).tolist(),
        "null_assumption": "Independent sign-exchangeable spectrum-level log ratios; not validated for a shared SDSS plate",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(diagnostic_report(), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()

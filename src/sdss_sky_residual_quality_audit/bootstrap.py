"""Uncertainty quantification: observational bootstrap and fit convergence checks.

Two deliberately separate functions per project-wide convention:
`bootstrap_statistic` resamples observational data (spectra) to get an
uncertainty on a summary statistic; `check_fit_convergence` inspects a
numerical continuum-fit's covariance matrix and reduced chi-square. They must
never be conflated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from sdss_sky_residual_quality_audit.exceptions import ConvergenceError, InsufficientDataError

DEFAULT_SEED = 20260713
DEFAULT_N_RESAMPLES = 1000


@dataclass(frozen=True)
class BootstrapResult:
    estimate: float
    lower: float
    upper: float
    n_resamples: int
    confidence_level: float


def bootstrap_statistic(
    values: np.ndarray,
    statistic: Callable[[np.ndarray], float] = np.median,
    *,
    n_resamples: int = DEFAULT_N_RESAMPLES,
    seed: int = DEFAULT_SEED,
    confidence_level: float = 0.68,
) -> BootstrapResult:
    """Bootstrap a confidence interval for `statistic(values)` by spectrum-level resampling.

    Deterministic given `seed`. Raises `InsufficientDataError` if fewer than
    2 values are supplied (cannot resample meaningfully).
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        raise InsufficientDataError(
            f"bootstrap_statistic requires >= 2 finite values, got {arr.size}"
        )
    if not (0.0 < confidence_level < 1.0):
        raise InsufficientDataError("confidence_level must be in (0, 1)")

    rng = np.random.default_rng(seed)
    n = arr.size
    resampled = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        resampled[i] = statistic(arr[idx])

    alpha = 1.0 - confidence_level
    lower = float(np.quantile(resampled, alpha / 2.0))
    upper = float(np.quantile(resampled, 1.0 - alpha / 2.0))
    point = float(statistic(arr))
    return BootstrapResult(
        estimate=point,
        lower=lower,
        upper=upper,
        n_resamples=n_resamples,
        confidence_level=confidence_level,
    )


@dataclass(frozen=True)
class ConvergenceCheck:
    converged: bool
    condition_number: float
    reduced_chi_square: float
    reason: str


def check_fit_convergence(
    covariance: np.ndarray,
    reduced_chi_square: float,
    *,
    max_condition_number: float = 1e8,
    chi_square_bounds: tuple[float, float] = (0.1, 10.0),
) -> ConvergenceCheck:
    """Check a numerical (continuum) fit's covariance conditioning and reduced chi-square.

    Not an observational bootstrap. Raises `ConvergenceError` if the
    covariance matrix is non-finite or empty; otherwise returns a
    `ConvergenceCheck` describing whether the fit is judged converged.
    """
    cov = np.asarray(covariance, dtype=float)
    if cov.size == 0 or not np.all(np.isfinite(cov)):
        raise ConvergenceError("fit covariance matrix is empty or contains non-finite entries")

    try:
        condition_number = float(np.linalg.cond(cov))
    except np.linalg.LinAlgError as exc:
        raise ConvergenceError(f"could not compute covariance condition number: {exc}") from exc

    if not np.isfinite(condition_number):
        raise ConvergenceError("covariance condition number is non-finite")

    chi_lo, chi_hi = chi_square_bounds
    reasons = []
    converged = True
    if condition_number > max_condition_number:
        converged = False
        reasons.append(f"condition number {condition_number:.3g} > {max_condition_number:.3g}")
    if not np.isfinite(reduced_chi_square):
        converged = False
        reasons.append("reduced chi-square is non-finite")
    elif not (chi_lo <= reduced_chi_square <= chi_hi):
        converged = False
        reasons.append(f"reduced chi-square {reduced_chi_square:.3g} outside [{chi_lo}, {chi_hi}]")

    reason = "converged" if converged else "; ".join(reasons)
    return ConvergenceCheck(
        converged=converged,
        condition_number=condition_number,
        reduced_chi_square=reduced_chi_square,
        reason=reason,
    )

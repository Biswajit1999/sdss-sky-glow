from __future__ import annotations

import numpy as np
import pytest

from sdss_sky_residual_quality_audit.bootstrap import bootstrap_statistic, check_fit_convergence
from sdss_sky_residual_quality_audit.exceptions import ConvergenceError, InsufficientDataError


def test_bootstrap_statistic_deterministic():
    values = np.linspace(1.0, 10.0, 50)
    r1 = bootstrap_statistic(values, seed=42, n_resamples=200)
    r2 = bootstrap_statistic(values, seed=42, n_resamples=200)
    assert r1 == r2


def test_bootstrap_statistic_interval_contains_estimate():
    values = np.linspace(1.0, 10.0, 50)
    result = bootstrap_statistic(values, n_resamples=500)
    assert result.lower <= result.estimate <= result.upper


def test_bootstrap_statistic_raises_on_too_few_values():
    with pytest.raises(InsufficientDataError):
        bootstrap_statistic(np.array([1.0]))


def test_bootstrap_statistic_rejects_bad_confidence_level():
    with pytest.raises(InsufficientDataError):
        bootstrap_statistic(np.array([1.0, 2.0, 3.0]), confidence_level=1.5)


def test_check_fit_convergence_well_conditioned():
    cov = np.eye(2) * 0.01
    result = check_fit_convergence(cov, reduced_chi_square=1.0)
    assert result.converged
    assert result.condition_number == pytest.approx(1.0)


def test_check_fit_convergence_flags_bad_chi_square():
    cov = np.eye(2) * 0.01
    result = check_fit_convergence(cov, reduced_chi_square=50.0)
    assert not result.converged
    assert "reduced chi-square" in result.reason


def test_check_fit_convergence_flags_ill_conditioned():
    cov = np.array([[1.0, 0.0], [0.0, 1e-12]])
    result = check_fit_convergence(cov, reduced_chi_square=1.0)
    assert not result.converged


def test_check_fit_convergence_raises_on_nonfinite_covariance():
    cov = np.array([[np.nan, 0.0], [0.0, 1.0]])
    with pytest.raises(ConvergenceError):
        check_fit_convergence(cov, reduced_chi_square=1.0)


def test_check_fit_convergence_raises_on_empty_covariance():
    with pytest.raises(ConvergenceError):
        check_fit_convergence(np.array([]), reduced_chi_square=1.0)

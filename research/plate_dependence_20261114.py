"""Conditional within-plate dependence audit; no measured SDSS covariance."""
import math

def design_effect(cluster_sizes, rho):
    """Variance inflation of an equal-weight mean under exchangeable clusters."""
    sizes = tuple(cluster_sizes)
    if not sizes or any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in sizes):
        raise ValueError("cluster sizes must be positive integers")
    if not math.isfinite(rho) or not 0 <= rho <= 1:
        raise ValueError("rho must be finite and between zero and one")
    n = sum(sizes)
    deff = 1 + rho * (sum(s * s for s in sizes) / n - 1)
    return {"n": n, "clusters": len(sizes), "design_effect": deff,
            "effective_n": n / deff, "se_multiplier": math.sqrt(deff)}

def leave_one_cluster_out(values, cluster_ids):
    """Cluster deletion estimates; requires at least two independent clusters."""
    x, ids = tuple(values), tuple(cluster_ids)
    if len(x) != len(ids) or not x or any(not math.isfinite(v) for v in x):
        raise ValueError("matched nonempty finite observations required")
    unique = tuple(dict.fromkeys(ids))
    if len(unique) < 2:
        raise ValueError("one plate cannot support leave-one-plate-out analysis")
    return {str(c): sum(v for v, k in zip(x, ids) if k != c) /
            sum(k != c for k in ids) for c in unique}

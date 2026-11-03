"""SDSS plate-level dependence sensitivity; synthetic examples only."""
import numpy as np

def effective_sample_size(n, intraclass_corr):
    """Equal-size exchangeable cluster design effect for one plate."""
    if n < 2 or not np.isfinite(intraclass_corr) or not (-1/(n-1) < intraclass_corr <= 1):
        raise ValueError('invalid exchangeable correlation')
    return n / (1 + (n - 1) * intraclass_corr)

def equicorrelated_mean_se(values, intraclass_corr):
    """Known marginal variance and exchangeable within-plate covariance."""
    x = np.asarray(values, float)
    if x.ndim != 1 or x.size < 2 or not np.all(np.isfinite(x)):
        raise ValueError('finite 1D sample required')
    neff = effective_sample_size(x.size, intraclass_corr)
    return float(np.std(x, ddof=1) / np.sqrt(neff))

def leave_one_plate_out(values, plates):
    """Identifiability check: plate-robust inference requires >=2 plates."""
    x = np.asarray(values, float)
    p = np.asarray(plates)
    if x.ndim != 1 or x.size != p.size or not np.all(np.isfinite(x)):
        raise ValueError('invalid rows')
    unique = np.unique(p)
    if unique.size < 2:
        raise ValueError('single plate: cannot estimate between-plate sensitivity')
    if any(np.count_nonzero(p != plate) == 0 for plate in unique):
        raise ValueError('empty retained sample')
    return {str(plate): float(np.mean(x[p != plate])) for plate in unique}

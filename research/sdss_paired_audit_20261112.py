"""Paired sky/control log-ratio sensitivity, one row per independent spectrum.

Rows remain paired across windows. Sign flips require exchangeability under the
sharp symmetric null; they are not valid for arbitrary asymmetric residuals.
"""
import itertools
import numpy as np

def _matrix(values):
    x=np.asarray(values,dtype=float)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < 1 or not np.isfinite(x).all():
        raise ValueError("finite 2D matrix with >=2 spectra required")
    return x

def paired_bootstrap(values, draws=2000, seed=42):
    """Return 2.5%, 50%, 97.5% quantiles of spectrum-level mean per window."""
    x=_matrix(values)
    if not isinstance(draws,int) or draws < 100:
        raise ValueError("draws >=100 required")
    rng=np.random.default_rng(seed)
    indices=rng.integers(0,len(x),size=(draws,len(x)))
    return np.quantile(x[indices].mean(axis=1),[.025,.5,.975],axis=0)

def leave_one_spectrum_out(values):
    """Per-window mean after each independent spectrum is removed."""
    x=_matrix(values)
    return (x.sum(axis=0)[None,:]-x)/(len(x)-1)

def exact_signflip_pvalues(values):
    """Two-sided exact paired sign-flip p-values; at most 18 spectra."""
    x=_matrix(values)
    n=len(x)
    if n>18:
        raise ValueError("exact enumeration capped at 18 spectra")
    observed=np.abs(x.mean(axis=0))
    extreme=np.zeros(x.shape[1],dtype=int)
    for signs in itertools.product((-1.,1.),repeat=n):
        means=np.abs((x*np.asarray(signs)[:,None]).mean(axis=0))
        extreme += means >= observed-1e-12
    return extreme/(2**n)

def holm_adjust(pvalues):
    """Holm step-down familywise adjusted p-values."""
    p=np.asarray(pvalues,dtype=float)
    if p.ndim!=1 or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError("valid p-values required")
    order=np.argsort(p)
    out=np.empty_like(p)
    out[order]=np.maximum.accumulate(np.minimum(1,(len(p)-np.arange(len(p)))*p[order]))
    return out

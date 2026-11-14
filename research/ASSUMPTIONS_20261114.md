# Conditional single-plate dependence audit (14 November 2026)

Scope: [issue #3](https://github.com/Biswajit1999/sdss-sky-glow/issues/3). Existing released DR17 sample comprises 15 spectra from one plate/MJD. It cannot identify between-plate variance. The code explicitly rejects leave-one-plate-out with a single plate.

The exchangeable model assumes identical marginal variances, independent clusters, and a common nonnegative within-cluster correlation rho. For cluster sizes m_j and total n, the equal-weight mean's variance inflation relative to independence is D = 1 + rho*(sum(m_j^2)/n - 1); n_eff = n/D. This is a **conditional sensitivity calculation**, not an estimate of SDSS correlation. Heteroscedasticity and cross-plate correlations are not modeled. The leave-one-cluster-out routine is only meaningful with >=2 independently sampled clusters.

Run: `cd research && python -m unittest -v test_plate_dependence_20261114.py`.
The accompanying SVG displays theoretical n_eff for one hypothetical cluster of 15; it is not an observational figure. Original spectra and published results are unchanged. Scientific implementation was assisted by AI; Biswajit Jana remains the requested authenticated commit author. No new observational discovery is claimed.

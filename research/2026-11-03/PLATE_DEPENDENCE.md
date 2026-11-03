# Plate-level dependence sensitivity (3 November 2026)

Issue #3. The retained SDSS DR17 observational sample consists of 15 spectra from a *single plate* (plate 266, MJD 51630). Consequently it is not possible to estimate between-plate variance or leave-one-plate-out robustness. The new code explicitly raises on that design rather than reporting a fictitious plate bootstrap.

For n exchangeable measurements with *hypothetical* common intraclass correlation rho, the design effect is 1+(n-1)rho, and the corresponding effective sample size is n divided by that factor. For n=15: rho=0 gives n_eff=15, rho=0.05 gives 8.824, rho=0.10 gives 6.25, rho=0.25 gives 3.333, rho=1 gives 1. These values are *sensitivity scenarios*, not measured SDSS correlations. The plug-in mean SE is a heuristic based on the sample standard deviation; estimating rho or population variance from one plate is not identified by this code.

Reproduce locally with NumPy and pytest: `cd research/2026-11-03 && python -m pytest -q test_plate_dependence.py`. No SDSS spectra or original observational results were modified. Scientific implementation prepared with AI assistance; commit attribution follows the authenticated repository identity.

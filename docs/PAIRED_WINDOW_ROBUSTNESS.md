# Paired SDSS sky-window robustness (30 October 2026)

Research issue: #1. This adds three *post-processing* sensitivity checks to the existing sky/control residual-scale ratio workflow. It does not change the continuum model or replace the DR17 spectra and provenance manifest.

## Methods

1. **Paired spectrum-level bootstrap.** For an `N_spectra × N_windows` matrix of strictly positive residual-scale ratios, take logarithms and resample entire spectrum rows using the *same indices for every window*. Report median ratios and percentile intervals. This preserves the empirical within-spectrum cross-window dependence, unlike independently resampling windows. NaNs represent missing windows, not zeros.
2. **Leave-one-spectrum-out influence.** Recompute the median log ratio after deleting each spectrum; report the maximum absolute shift in log units. This detects disproportionate leverage from a small retained sample and does not measure uncertainty due to unobserved plates.
3. **Sign-flip null and Holm correction.** Under independent, sign-exchangeable spectrum-level log ratios, enumerate all sign assignments for ≤16 spectra; otherwise use a seeded two-sided Monte Carlo test of mean log ratio zero, with a plus-one p-value correction. Apply Holm step-down adjustment across the predeclared five sky windows. This is a sensitivity calculation **conditional on the sign-exchangeability assumption**, which may fail for multiple fibres on one plate sharing sky subtraction and calibration.

## Provenance and limitations

The five window labels correspond to the repository's `windows.py`: [OI] 5577 Å, [OI] 6300 Å, Na D, [OI] 6364 Å and the OH onset region. The example uses 40 **seeded synthetic spectra** with shared correlated perturbations and injected excesses in two windows. It is not the existing 15-spectrum plate-266/MJD-51630 observational sample; the individual DR17 spectra are not committed in this repository. Therefore the synthetic p-values, intervals and effect sizes **must not** be quoted as new SDSS observational significance. Apply these functions to the existing real per-spectrum `PairExcess` results only after verifying source IDs, complete window coverage, covariance and cross-plate dependence.

## Reproduction

```bash
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_paired_window_diagnostics.py
python -m sdss_sky_residual_quality_audit.paired_window_diagnostics --output results/paired_window_synthetic.json
python scripts/plot_paired_window_diagnostics.py --output results/paired_window_synthetic.png
```

Existing repository tests and Ruff must pass before merging. The new runner creates generated JSON and PNG diagnostics and never downloads or overwrites observational inputs.

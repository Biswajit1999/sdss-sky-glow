# Research Blueprint

## Technical title

SDSS Night-Sky Residual Quality Audit

## Category

Spectroscopic instrumentation / data science

## Bounded scientific question

Do known night-sky wavelength regions show elevated uncertainty-normalised residual structure relative to matched local control windows?

## Gap statement

A released-product QA audit; not a new SDSS sky subtraction or raw reduction pipeline.

## First-release scope

The first release must be completable as a focused 4–6 hour implementation pass after data access is working. It must deliver one reproducible analysis pipeline, one deterministic example/smoke dataset, tests, 4–6 figures, a concise TeX report and a deployable research webpage.

## Validation and uncertainty

- synthetic residual injection
- spectrum-level bootstrap
- mask sensitivity
- shifted-window null test
- class/SNR stratification

## Required figures

1. representative spectra
2. local residual examples
3. scale by region
4. class comparison
5. SNR dependence
6. null test

## Reusable scientific modules

- `fetch.py`
- `io.py`
- `masks.py`
- `windows.py`
- `continuum.py`
- `residuals.py`
- `metrics.py`
- `bootstrap.py`
- `null_tests.py`

## Explicit exclusions

- No novelty claim beyond the bounded dataset/question/method combination.
- No causal claim from descriptive catalogue correlations.
- No hidden manual data editing.
- No unsupported precision beyond the input uncertainties.
- No production-pipeline replacement claim.

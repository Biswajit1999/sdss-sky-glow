# Implementation Plan — SDSS Night-Sky Residual Quality Audit

Author: Biswajit Jana. Local Claude Code implementation pass (portfolio project,
`BUILD_FIRST`, priority 9.2/10). Reference implementations: the completed sibling
projects `hst-acs-two-axis-cte-audit`, `euclid-q1-vis-psf-astrometry-audit`,
`hst-wfc3ir-ramp-linearity-audit` (all at `C:\Users\biswa\Documents\GitHub\`).

## 1. Scientific question and scope

Do known night-sky wavelength regions show elevated uncertainty-normalised residual
structure relative to matched local control windows? Bounded QA audit of released
SDSS spectra, not a new sky-subtraction pipeline.

## 2. Literature verification (done 2026-07-13/14, before coding)

All verified live via WebFetch/CrossRef; none required inventing metadata.

1. **Ahn et al. 2012**, "The Ninth Data Release of the Sloan Digital Sky Survey:
   First Spectroscopic Data from ... BOSS", ApJS 203, 21. arXiv:1207.7137.
   Verified via arxiv.org/abs page.
2. **Guy et al. 2023**, "The Spectroscopic Data Processing Pipeline for the Dark
   Energy Spectroscopic Instrument", AJ. arXiv:2209.14482. Verified via arxiv.org/abs.
3. **Noll et al. 2014**, "Skycorr: A general tool for spectroscopic sky
   subtraction", A&A 567, A25. DOI 10.1051/0004-6361/201423908. Verified via
   doi.org redirect to aanda.org.
4. **SDSS DR17 spectro basics** — https://www.sdss4.org/dr17/spectro/spectro_basics/
   Verified live: wavelength coverage (SDSS 3800-9200A, BOSS 3650-10400A), vacuum
   wavelength convention confirmed explicitly.
5. **SDSS DR17 bitmasks (SPPIXMASK)** —
   https://www.sdss4.org/dr17/algorithms/bitmasks/#SPPIXMASK — Verified live, full
   32-bit table extracted. Directly usable for `masks.py`. This page **explicitly
   states** that pipeline error estimates "can be untrustworthy near certain
   emission lines like 5577 Angstroms" — a direct, citable, non-fabricated source
   for treating 5577A as a documented problem wavelength.
6. **SDSS spec FITS datamodel** —
   https://data.sdss.org/datamodel/files/BOSS_SPECTRO_REDUX/RUN2D/spectra/full/PLATE4/spec.html
   Verified live: HDU1 COADD columns (flux, loglam, ivar, and_mask, or_mask, wdisp,
   sky, model).
7. **Added supplementary citation, verified via CrossRef API**: Hanuschik (2003),
   "A flux-calibrated, high-resolution atlas of optical sky emission from UVES",
   A&A 407, 1157-1164. DOI 10.1051/0004-6361:20030885. Standard reference atlas
   covering the SDSS optical range (3140-10430A vs SDSS's 3800-10400A), used to
   justify the [OI]/NaD/OH-forest window list as literature-documented airglow
   features rather than values recalled from memory alone.

No citation required a `TODO_VERIFY` marker — all 6 original + 1 supplementary
resolved to real, matching primary sources.

## 3. Real-data access plan (verified live against astroquery.sdss, not assumed)

`astroquery.sdss.SDSSClass` (astroquery 0.4.7, confirmed via
astroquery.readthedocs.io API docs) exposes `query_sql`/`query_sql_async`
(arbitrary SQL against the SDSS CasJobs mirror, default `data_release=17`) and
`get_spectra` (`matches=<Table>` -> `list[HDUList]`). Plan:

1. `query_sql` a deterministic SELECT against `SpecObj` for a small, class-diverse,
   deterministic sample (mix of GALAXY/STAR/QSO, `zWarning=0`, a spread of
   `snMedian`), `ORDER BY specobjid`, `TOP N`.
2. `get_spectra(matches=<result table>)` to download each spectrum's `spec-*.fits`
   (small, single-object coadd files, each a few hundred KB).
3. Record manifest rows with real SHA-256 of the downloaded bytes.
4. Public-access note: SDSS data (all public data releases, including DR17) are
   released under an open data policy requiring only acknowledgement of SDSS —
   https://www.sdss4.org/collaboration/citing-sdss/ (standard, well known SDSS
   data-use policy; no login/paywall on the DR17 CasJobs SQL or spectrum-download
   endpoints used here).

## 4. Module design (`src/sdss_sky_residual_quality_audit/`)

Following `docs/RESEARCH_BLUEPRINT.md`'s explicit module list.

- `config.py` — typed `AnalysisConfig` loader for `config/analysis.yml` (ported
  from sibling projects, ~verbatim).
- `exceptions.py` — extend existing `ProjectError`/`DataSchemaError`/
  `ProvenanceError` stub with `ArchiveAccessError`, `ConvergenceError`,
  `InsufficientDataError`.
- `logging_utils.py` — new module, ported near-verbatim from siblings.
- `provenance.py` — extend existing `sha256_file` stub with `sha256_bytes`,
  `sha256_config`, `get_git_commit`, `ManifestRow`/`append_manifest_row`/
  `read_manifest`.
- `results_io.py` — new module: `Metric` dataclass + `write_summary`/
  `validate_summary`, matching `results/summary.schema.json`.
- `synthetic.py` — new module: synthetic spectrum generator with a known-amplitude
  injected excess-noise bump at a chosen wavelength (continuum + Gaussian-ish noise
  inflation), shared by `tests/conftest.py` fixtures and `--demo`.
- `fetch.py` — real SQL query + `get_spectra` download, `ArchiveAccessError` on any
  query/access failure (implementation lives in `scripts/fetch_data.py`, this
  module holds the reusable, testable query/selection helpers).
- `io.py` — load a downloaded `spec-*.fits` (or in-memory `HDUList`) into a typed
  `Spectrum` (wavelength Angstrom vacuum = `10**loglam`, flux, ivar, and_mask,
  or_mask, class/subclass/z from HDU2). Raises `DataSchemaError` on missing
  HDU/columns.
- `masks.py` — verified SPPIXMASK bit table; `good_pixel_mask` (hard-quality bits +
  ivar<=0/non-finite only, sky-quality bits deliberately NOT excluded by default
  since they are the subject under study); `sky_quality_flag_mask` (NOSKY/
  BRIGHTSKY/BADSKYCHI/REDMONSTER) for the mask-sensitivity validation check.
- `windows.py` — night-sky line window list ([OI]5577, NaD 5890, [OI]6300/6364,
  broad OH airglow forest region) + matched local control window placement
  (same width, offset in wavelength, avoiding all sky windows and spectral edges).
- `continuum.py` — robust local continuum estimate per window via a low-order
  weighted polynomial fit (ivar-weighted, normalized x-axis for conditioning) over
  a surrounding baseline region excluding the window itself; returns fit +
  covariance for convergence checking.
- `residuals.py` — per-pixel uncertainty-normalised residual: `(flux - continuum) *
  sqrt(ivar)`; per-window aggregate statistic (robust std / RMS) with masking.
- `metrics.py` — per-spectrum, per-window-pair excess statistic: sky-window
  residual scale vs. matched control-window residual scale (ratio and difference);
  cross-spectrum aggregation (median, class/SNR stratified).
- `bootstrap.py` — `bootstrap_statistic` (spectrum-level resampling, 1000
  resamples, seed 20260713) **and** `check_fit_convergence` (continuum-fit
  covariance condition number + reduced chi-square) as two separate, non-conflated
  functions (per project-wide convention; this project's blueprint names the
  uncertainty module `bootstrap.py` rather than `uncertainty.py`).
- `null_tests.py` — shifted-window null test (both "windows" placed at matched
  control locations, no known sky line involved) + class/SNR stratification
  helpers.
- `plotting.py` — extend existing `plot_demo` stub; figure-specific plotting logic
  lives inline in `scripts/make_figures.py` (matches sibling pattern).
- `core.py` — `run_pipeline` orchestrator: per-spectrum try/except catching
  `InsufficientDataError`/`ConvergenceError`/`DataSchemaError` -> warning, never
  aborts the whole run; raises `InsufficientDataError` immediately on empty input.

## 5. Validation contract mapping

- synthetic residual injection -> `synthetic.py` + `tests/test_residuals.py` /
  `test_core_pipeline.py` injection-recovery gate.
- spectrum-level bootstrap -> `bootstrap.bootstrap_statistic` over per-spectrum
  window excess statistics.
- mask sensitivity -> rerun with `sky_quality_flag_mask` bits also excluded;
  compare excess-statistic magnitude with/without.
- shifted-window null test -> `null_tests.py`, comparing two matched control
  windows against each other (no true sky line difference expected).
- class/SNR stratification -> `metrics.py` grouping by SDSS `class` and
  `snMedian`-derived SNR bins.

## 6. Scripts

- `scripts/fetch_data.py` — gated behind `--i-have-authorization`; deterministic
  SQL sample; real SHA-256 manifest rows.
- `scripts/run_analysis.py` — `--demo` synthetic smoke path vs. real-data path
  (`SystemExit` if manifest missing/empty); `tracemalloc` + `perf_counter`
  benchmarks.
- `scripts/make_figures.py` — `make_demo_figures`/`make_real_figures`, 6 required
  figures as SVG+PNG(300dpi)+sidecar JSON.
- `scripts/sync_web_assets.py` — copy `results/*.json`, `figures/*.{svg,json}`,
  `data/manifest.csv` into `web-react/public/`.

## 7. Web dashboard

- Fix `eslint.config.js` (`react/jsx-uses-vars`, `react/jsx-uses-react`).
- Remove unused `recharts` from `web-react/package.json`.
- Rewrite `App.jsx` from the `hst-wfc3ir-ramp-linearity-audit` template.
- Rewrite `public/project.json` with this project's real fields.

## 8. Report

- `reports/report.tex` + `reports/references.bib` — full sections, real figures,
  `natbib`/`\citep`, only pipeline-produced numbers.

## 9. Order of work

Foundation -> data layer (fetch+synthetic) -> scientific modules -> tests/pytest
-> ruff/mypy -> demo figures -> report skeleton with demo numbers -> web dashboard
(demo) -> **real data fetch (after this-session authorization, already granted)**
-> real pipeline run -> real figures -> report update with real numbers -> final
verification pass -> `LOCAL_COMPLETION_REPORT.md` + `_PROJECT_LOG.md`.

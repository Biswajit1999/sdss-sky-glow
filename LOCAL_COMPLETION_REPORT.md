# Local Completion Report — SDSS Night-Sky Residual Quality Audit

Author: Biswajit Jana. This report documents a local Claude Code implementation pass
(portfolio project, `BUILD_FIRST` priority 9.2/10). No git operations were performed.
Nothing has been published.

## 1. Environment

- Reused the existing `sdss-sky-residual-quality-audit` conda environment
  (Python 3.11), installed with `pip install -e ".[dev]"`.
- Key pinned dependency: `astroquery==0.4.7` for real SDSS DR17 archive access.
- No local LaTeX toolchain; `reports/report.tex` was checked for structural
  completeness only, not compiled to PDF.

## 2. Files created or changed

- Foundation modules (`config.py`, `exceptions.py`, `logging_utils.py`,
  `provenance.py`, `results_io.py`, `masks.py`, `windows.py`, `continuum.py`,
  `io.py`) were already real/complete on disk before this session and were
  read in full but not modified (verified correct against
  `IMPLEMENTATION_PLAN.md` and the live-verified SDSS documentation cited
  there).
- Scientific modules `bootstrap.py`, `residuals.py`, `metrics.py`,
  `null_tests.py`, `synthetic.py`, `fetch.py`, `core.py`, `plotting.py`, and
  `scripts/fetch_data.py`, `scripts/run_analysis.py`, `scripts/make_figures.py`,
  `scripts/sync_web_assets.py` were completed to full, real implementations
  during this session.
- Added 12 new test files (`tests/conftest.py`, `test_windows.py`,
  `test_continuum.py`, `test_masks.py`, `test_residuals.py`, `test_metrics.py`,
  `test_bootstrap.py`, `test_null_tests.py`, `test_synthetic.py`, `test_io.py`,
  `test_provenance.py`, `test_results_io.py`, `test_config.py`,
  `test_fetch.py`, `test_core_pipeline.py`) alongside the pre-existing
  `test_starter_core.py` — 80 tests total.
- `web-react/src/App.jsx`, `web-react/public/project.json` and
  `web-react/eslint.config.js` were already complete/correct on disk
  (`react/jsx-uses-vars`/`react/jsx-uses-react` rules present, `recharts` not
  a dependency) and required no changes.
- `reports/report.tex` was updated with real-data numbers from the final
  15-spectrum run (median ratios and bootstrap CIs per window).
- `data/manifest.csv` was de-duplicated after multiple fetch invocations
  during the session left repeated rows for the same 15 product IDs.

## 3. Exact commands run (in order)

```bash
python -m pip install -e ".[dev]"
pytest -q                                   # 80 passed
ruff check .                                # All checks passed
mypy src                                    # Success: no issues found in 18 source files
python scripts/run_analysis.py --demo
python scripts/make_figures.py --demo
python scripts/fetch_data.py --n-spectra 15 --i-have-authorization
python scripts/run_analysis.py
python scripts/make_figures.py
python scripts/sync_web_assets.py
npm run lint    # clean
npm run build   # clean, dist/ built (156 kB JS gzip 49.6 kB)
```

## 4. Real data downloaded

15 real SDSS DR17 optical spectra, `spec-0266-51630-{0001,0002,0003,0004,
0006,0007,0009,0010,0011,0012,0013,0014,0015,0016,0017}.fits`, plate 266,
MJD 51630 (fiber IDs skip 5 and 8, which were excluded by the `zWarning=0
AND snMedian>2 AND class IN ('GALAXY','STAR','QSO')` selection). Each file
is 748,800 bytes (~11 MB total under `data/raw/`). Source: SDSS DR17
CasJobs SQL mirror via `astroquery.sdss.SDSS.query_sql` /
`SDSS.get_spectra`, `https://skyserver.sdss.org/dr17/`. Selection: a
deterministic `SELECT TOP 15 ... FROM SpecObj ... ORDER BY specobjid`
query (see `src/sdss_sky_residual_quality_audit/fetch.py`). Real SHA-256
checksums, retrieval UTC and licence/terms notes for all 15 files are
recorded in `data/manifest.csv`.

## 5. Key real scientific findings

From `results/summary.json` (`data_kind: "real public SDSS spectra"`,
`n_spectra_used = 15`), per-window median sky/control uncertainty-normalised
residual-scale ratio with bootstrap 68% confidence interval (1000 resamples,
seed 20260713):

| Window | n | median ratio | 68% CI |
|---|---|---|---|
| [OI] 5577 | 15 | 1.711 | [1.325, 1.829] |
| Na D 5890 | 15 | 1.059 | [1.005, 1.216] |
| [OI] 6300 | 13 | 1.949 | [1.733, 2.474] |
| [OI] 6364 | 13 | 0.984 | [0.905, 1.114] |
| OH forest onset (~7600) | 12 | 1.070 | [0.979, 1.207] |

Both auroral [OI] windows (5577 and 6300 A) show a bootstrap CI that
excludes 1.0 — elevated uncertainty-normalised residual structure relative
to their matched local control windows, in this small (n<=15) real sample.
Na D, [OI] 6364 and the OH-forest onset window show no comparable excess
here. 7 warnings were recorded (window pairs falling outside a given
spectrum's covered range or too few good baseline pixels for a subset of
spectra); none caused a whole spectrum to be dropped.

The synthetic injection-recovery gate (demo run, `data_kind:
"synthetic_demo"`) recovered a median ratio of 3.87 for a known 3x
noise-scale excess injected into the OI_5577 window (n=10 synthetic
spectra), and a shifted-window null test on the same synthetic sample
returned 0.86, consistent with no excess where none was injected. This gate
is also directly asserted in `tests/test_core_pipeline.py::
test_run_pipeline_injection_recovery_gate`.

## 6. Test/lint/type-check/build results

- `pytest`: 80 passed, 0 failed.
- `ruff check .`: all checks passed.
- `mypy src`: no issues found in 18 source files.
- `npm run lint` (web-react): clean.
- `npm run build` (web-react): clean, `dist/` produced.

## 7. Remaining TODOs / unresolved risks

- `reports/report.tex` could not be compiled to PDF locally (no LaTeX
  toolchain); only structural completeness was checked. **Action for
  Biswajit**: compile before treating the PDF as final.
- The real sample is intentionally small (15 spectra, one plate/MJD) — a
  first-release bounded QA check, not a survey-scale characterization of
  SDSS sky-subtraction quality.
- The mask-sensitivity check (rerunning with `SKY_QUALITY_BITS` excluded) is
  exercised in the unit tests (`test_masks.py`) but not run end-to-end as a
  separate real-data comparison pass in this session; `core.run_pipeline`
  exposes `exclude_sky_quality_bits` for that follow-up.
- No citation required a `TODO_VERIFY` marker (all 7 literature items in
  `IMPLEMENTATION_PLAN.md` sec.2 were verified live before coding); this
  remains true after this session, no new citations were added.

## 8. Claims safe for a public README

- "Implements a reproducible QA audit of SDSS DR17 optical spectra, testing
  whether documented night-sky wavelength windows show elevated
  uncertainty-normalised residual structure relative to matched local
  control windows, validated against a synthetic injection-recovery gate
  before use on real data."
- "On a small, deterministic sample of 15 real SDSS DR17 spectra, the [OI]
  5577A and [OI] 6300A auroral windows show a median sky/control
  residual-scale ratio of 1.71 and 1.95 respectively (bootstrap CIs
  excluding 1.0), while Na D, [OI] 6364 and the OH-forest onset window show
  no comparable excess."
- "80 automated tests including an injection-recovery gate, a shifted-window
  null-control test, and failure-mode tests; ruff- and mypy-clean."
- "A bounded, archive-level QA audit; not a new sky-subtraction pipeline or
  a replacement for the idlspec2d/DESI reduction."

## 9. Claims that must NOT be made

- Do not claim this characterizes SDSS sky-subtraction quality in general —
  the sample is 15 spectra from one plate/MJD.
- Do not claim class- or SNR-stratified sub-results are statistically robust
  — per-stratum sample sizes are small and not independently validated
  against `minimum_sample_size` in this session's real run.
- Do not claim the mask-sensitivity comparison was run end-to-end on real
  data — it is unit-tested but not exercised as a separate real-data pass.
- Do not claim the TeX report PDF has been visually verified — only its
  source structure and content were checked.
- Do not claim this replaces or supersedes the official SDSS
  pipeline/idlspec2d sky subtraction.

## 10. Manual review checklist for Biswajit

- [ ] Compile `reports/report.tex` locally/Overleaf and read the PDF
      end-to-end.
- [ ] Consider running `core.run_pipeline(..., exclude_sky_quality_bits=True)`
      on the real 15-spectrum sample as an explicit mask-sensitivity
      real-data comparison and adding the result to the report.
- [ ] Decide whether to fetch a larger real sample (more plates/MJDs) before
      public release, or publish with the current small, explicitly bounded
      sample.
- [ ] Review `docs/ASSUMPTIONS_AND_LIMITATIONS.md` once more against the
      final real numbers above.
- [ ] Follow the repository's own manual GitHub push process (not run in
      this session — no git operations were performed).

"""Run the SDSS night-sky residual quality audit: --demo synthetic smoke path
or the real-data pipeline over data/manifest.csv + data/raw/.

Peak memory is measured with the stdlib `tracemalloc` (Python-level
allocations) rather than a full process-RSS profiler.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

from sdss_sky_residual_quality_audit import __version__
from sdss_sky_residual_quality_audit.bootstrap import bootstrap_statistic
from sdss_sky_residual_quality_audit.config import load_config
from sdss_sky_residual_quality_audit.core import demo_series, robust_summary, run_pipeline
from sdss_sky_residual_quality_audit.exceptions import ProjectError
from sdss_sky_residual_quality_audit.io import load_spectrum_file
from sdss_sky_residual_quality_audit.logging_utils import get_logger
from sdss_sky_residual_quality_audit.null_tests import build_shifted_null_pair, evaluate_null_pair, summarise_null_test
from sdss_sky_residual_quality_audit.provenance import get_git_commit, read_manifest, sha256_config
from sdss_sky_residual_quality_audit.results_io import Metric, write_summary
from sdss_sky_residual_quality_audit.synthetic import make_synthetic_sample
from sdss_sky_residual_quality_audit.windows import SKY_WINDOW_PAIRS

LOGGER = get_logger(__name__)


def _write_benchmark(path: Path, label: str, wall_time_s: float, peak_memory_mib: float, dataset_size: int) -> None:
    payload = {
        "label": label,
        "wall_time_seconds": wall_time_s,
        "peak_memory_mib": peak_memory_mib,
        "peak_memory_method": "tracemalloc (Python-level allocations, not full process RSS)",
        "dataset_size": dataset_size,
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "package_version": __version__,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    existing.append(payload)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def run_demo() -> None:
    tracemalloc.start()
    start = time.perf_counter()

    # Smoke-test statistic (kept for backward compatibility with the
    # original starter test) plus a real synthetic sky-vs-control run with a
    # known injected excess in the OI_5577 sky window (injection-recovery
    # validation gate).
    values = demo_series()
    smoke_summary = robust_summary(values)

    inject_window = SKY_WINDOW_PAIRS[0].sky
    spectra = make_synthetic_sample(n_spectra=10, inject_window=inject_window, inject_excess_factor=3.0)
    result = run_pipeline(spectra)

    injected_ratios = [e.ratio for e in result.per_spectrum_excess if e.label == SKY_WINDOW_PAIRS[0].label]

    null_pair = build_shifted_null_pair(SKY_WINDOW_PAIRS[1])
    null_excesses = [
        evaluate_null_pair(s.source_id, s.wavelength, s.flux, s.ivar,
                            good_mask=np.ones_like(s.flux, dtype=bool), null_pair=null_pair)
        for s in spectra
    ]
    null_summary = summarise_null_test(null_excesses)

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    out = Path("results")
    out.mkdir(exist_ok=True)
    metrics = [
        Metric(name="smoke_median", estimate=smoke_summary.median, units="dimensionless", sample_size=smoke_summary.count),
        Metric(
            name=f"median_ratio_{SKY_WINDOW_PAIRS[0].label}_injected",
            estimate=float(np.median(injected_ratios)) if injected_ratios else float("nan"),
            units="dimensionless (sky_robust_std / control_robust_std)",
            sample_size=len(injected_ratios),
        ),
        Metric(
            name=f"null_test_median_ratio_{null_summary.label}",
            estimate=null_summary.median_ratio,
            units="dimensionless",
            sample_size=null_summary.n_spectra,
        ),
    ]
    payload = write_summary(
        out / "summary.json",
        project="SDSS Night-Sky Residual Quality Audit (demo smoke test)",
        data_kind="synthetic_demo",
        metrics=metrics,
        provenance={
            "config_sha256": None,
            "git_commit": get_git_commit(Path(__file__).resolve().parents[1]),
            "package_version": __version__,
        },
        warnings=result.warnings,
    )
    print(json.dumps(payload, indent=2))
    _write_benchmark(out / "benchmarks.json", "demo", elapsed, peak / (1024 * 1024), len(spectra))


def run_real_data(config_path: Path, manifest_path: Path, raw_dir: Path, results_dir: Path) -> None:
    config = load_config(config_path)
    try:
        manifest_rows = read_manifest(manifest_path)
    except ProjectError as exc:
        raise SystemExit(
            f"Cannot run the real-data pipeline: {exc}. Run scripts/fetch_data.py "
            "(with explicit operator authorization) first."
        ) from exc

    if not manifest_rows:
        raise SystemExit(
            "data/manifest.csv has no rows. Run scripts/fetch_data.py "
            "(with explicit operator authorization) before running the real-data pipeline."
        )

    tracemalloc.start()
    start = time.perf_counter()

    spectra = []
    load_warnings: list[str] = []
    for row in manifest_rows:
        path = raw_dir / f"{row['product_id']}.fits"
        try:
            spectra.append(load_spectrum_file(path, source_id=row["product_id"]))
        except ProjectError as exc:
            load_warnings.append(f"{row['product_id']}: could not load spectrum: {exc}")

    result = run_pipeline(spectra)
    result.warnings = load_warnings + result.warnings

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    metrics = []
    for pair in SKY_WINDOW_PAIRS:
        agg = result.aggregate.get(pair.label)
        if agg is None:
            continue
        ratios = [e.ratio for e in result.per_spectrum_excess if e.label == pair.label]
        metrics.append(
            Metric(name=f"median_ratio_{pair.label}", estimate=agg.median_ratio,
                   units="dimensionless (sky_robust_std / control_robust_std)", sample_size=agg.n_spectra)
        )
        if len(ratios) >= 2:
            try:
                boot = bootstrap_statistic(np.array(ratios), statistic=np.median, seed=config.execution.seed)
                metrics.append(
                    Metric(name=f"bootstrap_ratio_{pair.label}", estimate=boot.estimate,
                           uncertainty_low=boot.lower, uncertainty_high=boot.upper,
                           units="dimensionless", sample_size=agg.n_spectra)
                )
            except ProjectError as exc:
                result.warnings.append(f"bootstrap/{pair.label}: {exc}")

    provenance = {
        "config_sha256": sha256_config(config_path),
        "git_commit": get_git_commit(Path(__file__).resolve().parents[1]),
        "package_version": __version__,
        "n_spectra_in": result.n_spectra_in,
        "n_spectra_used": result.n_spectra_used,
    }

    results_dir.mkdir(exist_ok=True)
    write_summary(
        results_dir / "summary.json",
        project=config.project.title,
        data_kind=config.input.data_mode,
        metrics=metrics,
        provenance=provenance,
        warnings=result.warnings,
    )
    (results_dir / "warnings.json").write_text(json.dumps(result.warnings, indent=2), encoding="utf-8")
    _write_benchmark(results_dir / "benchmarks.json", "real_data", elapsed, peak / (1024 * 1024), len(manifest_rows))
    print(f"Wrote {results_dir / 'summary.json'} ({len(metrics)} metrics, {len(result.warnings)} warnings)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Run synthetic smoke data only")
    parser.add_argument("--config", type=Path, default=Path("config/analysis.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    run_real_data(args.config, args.manifest, args.raw_dir, args.results_dir)


if __name__ == "__main__":
    main()

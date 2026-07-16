"""Generate the 6 required figures (docs/FIGURE_AND_UI_SPEC.md) as SVG + 300 dpi
PNG, each with a sidecar JSON recording git commit, config hash, sample size
and units.

--demo builds figures from the clearly-labelled synthetic data model in
`sdss_sky_residual_quality_audit.synthetic`. The real-data path reads
data/manifest.csv + data/raw/ and must only be run after
scripts/run_analysis.py (real mode) has produced validated results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from sdss_sky_residual_quality_audit import __version__
from sdss_sky_residual_quality_audit.config import load_config
from sdss_sky_residual_quality_audit.core import demo_series, run_pipeline
from sdss_sky_residual_quality_audit.io import load_spectrum_file
from sdss_sky_residual_quality_audit.masks import good_pixel_mask
from sdss_sky_residual_quality_audit.metrics import stratify_by_class, stratify_by_snr
from sdss_sky_residual_quality_audit.null_tests import build_shifted_null_pair, evaluate_null_pair
from sdss_sky_residual_quality_audit.plotting import plot_demo
from sdss_sky_residual_quality_audit.provenance import get_git_commit, read_manifest, sha256_config
from sdss_sky_residual_quality_audit.synthetic import make_synthetic_sample
from sdss_sky_residual_quality_audit.windows import SKY_WINDOW_PAIRS


def _sidecar(path: Path, *, data_kind: str, sample_size: int, units: str, config_path: Path, extra: dict | None = None) -> None:
    payload = {
        "figure": path.stem,
        "data_kind": data_kind,
        "sample_size": sample_size,
        "units": units,
        "git_commit": get_git_commit(Path(__file__).resolve().parents[1]),
        "config_sha256": sha256_config(config_path) if config_path.is_file() else None,
        "package_version": __version__,
    }
    if extra:
        payload.update(extra)
    path.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _save(fig, out_dir: Path, name: str) -> Path:
    svg_path = out_dir / f"{name}.svg"
    png_path = out_dir / f"{name}.png"
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=300)
    plt.close(fig)
    return png_path


def make_demo_figures(out_dir: Path, config_path: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data_kind = "synthetic_demo"

    inject_window = SKY_WINDOW_PAIRS[0].sky
    spectra = make_synthetic_sample(n_spectra=10, inject_window=inject_window, inject_excess_factor=3.0)
    result = run_pipeline(spectra)

    # 1. representative spectra
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for s in spectra[:3]:
        ax.plot(s.wavelength, s.flux, lw=0.7, alpha=0.8, label=s.source_id)
    for pair in SKY_WINDOW_PAIRS:
        ax.axvspan(pair.sky.low, pair.sky.high, color="tab:red", alpha=0.15)
    ax.set_xlabel("Wavelength (Angstrom, vacuum)")
    ax.set_ylabel("Flux (arb. units)")
    ax.set_title("Representative spectra — SYNTHETIC DEMO (shaded = sky windows)")
    ax.legend(fontsize=7)
    path = _save(fig, out_dir, "fig01_representative_spectra")
    _sidecar(path, data_kind=data_kind, sample_size=3, units="Angstrom vs arb. flux", config_path=config_path)

    # 2. local residual examples (one spectrum, sky window with injected excess)
    s0 = spectra[0]
    good = good_pixel_mask(s0.flux, s0.ivar, s0.and_mask)
    from sdss_sky_residual_quality_audit.continuum import fit_local_continuum
    from sdss_sky_residual_quality_audit.residuals import normalised_residuals
    fit = fit_local_continuum(s0.wavelength, s0.flux, s0.ivar, good, SKY_WINDOW_PAIRS[0].sky)
    resid = normalised_residuals(s0.wavelength, s0.flux, s0.ivar, good, fit)
    in_plot = (s0.wavelength >= SKY_WINDOW_PAIRS[0].sky.low - 60) & (s0.wavelength <= SKY_WINDOW_PAIRS[0].sky.high + 60)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(s0.wavelength[in_plot], resid[in_plot], lw=0.8, color="tab:blue")
    ax.axvspan(SKY_WINDOW_PAIRS[0].sky.low, SKY_WINDOW_PAIRS[0].sky.high, color="tab:red", alpha=0.15, label="sky window (injected excess)")
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xlabel("Wavelength (Angstrom, vacuum)")
    ax.set_ylabel("Uncertainty-normalised residual")
    ax.set_title(f"Local residual example — SYNTHETIC DEMO ({s0.source_id})")
    ax.legend(fontsize=8)
    path = _save(fig, out_dir, "fig02_local_residual_example")
    _sidecar(path, data_kind=data_kind, sample_size=int(np.sum(in_plot)), units="dimensionless residual vs Angstrom", config_path=config_path)

    # 3. scale by region (median ratio per window-pair label, with injected excess visible)
    labels = [p.label for p in SKY_WINDOW_PAIRS]
    medians = [result.aggregate[label].median_ratio if label in result.aggregate else np.nan for label in labels]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(labels, medians, color="tab:orange")
    ax.axhline(1.0, color="black", ls="--", lw=0.8, label="ratio = 1 (no excess)")
    ax.set_ylabel("Median sky/control residual-scale ratio")
    ax.set_title("Scale by region — SYNTHETIC DEMO (window with injected excess stands out)")
    ax.tick_params(axis="x", rotation=30)
    ax.legend()
    path = _save(fig, out_dir, "fig03_scale_by_region")
    _sidecar(path, data_kind=data_kind, sample_size=len(spectra), units="dimensionless ratio", config_path=config_path)

    # 4. class comparison
    classes = {s.source_id: s.obj_class for s in spectra}
    groups = stratify_by_class(result.per_spectrum_excess, classes)
    group_labels = sorted(g for g in groups if groups[g])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot([[e.ratio for e in groups[g]] for g in group_labels], tick_labels=group_labels)
    ax.axhline(1.0, color="black", ls="--", lw=0.8)
    ax.set_ylabel("Sky/control residual-scale ratio")
    ax.set_title("Class comparison — SYNTHETIC DEMO (all spectra tagged GALAXY)")
    path = _save(fig, out_dir, "fig04_class_comparison")
    _sidecar(path, data_kind=data_kind, sample_size=len(result.per_spectrum_excess), units="dimensionless ratio", config_path=config_path)

    # 5. SNR dependence
    snr = {s.source_id: s.sn_median for s in spectra}
    snr_groups = stratify_by_snr(result.per_spectrum_excess, snr, bins=(0.0, 15.0, 25.0, float("inf")), labels=("low_snr", "mid_snr", "high_snr"))
    snr_labels = [g for g in ("low_snr", "mid_snr", "high_snr") if snr_groups[g]]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot([[e.ratio for e in snr_groups[g]] for g in snr_labels], tick_labels=snr_labels)
    ax.axhline(1.0, color="black", ls="--", lw=0.8)
    ax.set_ylabel("Sky/control residual-scale ratio")
    ax.set_title("SNR dependence — SYNTHETIC DEMO")
    path = _save(fig, out_dir, "fig05_snr_dependence")
    _sidecar(path, data_kind=data_kind, sample_size=sum(len(snr_groups[g]) for g in snr_labels), units="dimensionless ratio", config_path=config_path)

    # 6. null test: shifted-window null pair vs the true injected-sky-window pair
    null_pair = build_shifted_null_pair(SKY_WINDOW_PAIRS[0])
    null_excesses = [
        evaluate_null_pair(s.source_id, s.wavelength, s.flux, s.ivar,
                            good_mask=good_pixel_mask(s.flux, s.ivar, s.and_mask), null_pair=null_pair)
        for s in spectra
    ]
    injected_ratios = [e.ratio for e in result.per_spectrum_excess if e.label == SKY_WINDOW_PAIRS[0].label]
    null_ratios = [e.ratio for e in null_excesses]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot([injected_ratios, null_ratios], tick_labels=["injected sky window", "shifted null (no line)"])
    ax.axhline(1.0, color="black", ls="--", lw=0.8, label="ratio = 1 (no excess)")
    ax.set_ylabel("Residual-scale ratio")
    ax.set_title("Null test — SYNTHETIC DEMO (injection-recovery + null-control gate)")
    ax.legend()
    path = _save(fig, out_dir, "fig06_null_test")
    _sidecar(path, data_kind=data_kind, sample_size=len(spectra), units="dimensionless ratio", config_path=config_path)

    print(f"Wrote 6 demo figures (SVG+PNG+JSON) to {out_dir}")


def make_real_figures(out_dir: Path, config_path: Path, manifest_path: Path, raw_dir: Path) -> None:
    config = load_config(config_path)
    manifest_rows = read_manifest(manifest_path)
    if not manifest_rows:
        raise SystemExit(
            "data/manifest.csv has no rows. Run scripts/fetch_data.py (with explicit "
            "operator authorization) and scripts/run_analysis.py before generating real figures."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    data_kind = config.input.data_mode

    spectra = []
    for row in manifest_rows:
        path = raw_dir / f"{row['product_id']}.fits"
        try:
            spectra.append(load_spectrum_file(path, source_id=row["product_id"]))
        except Exception:  # noqa: BLE001
            continue
    result = run_pipeline(spectra)

    # 1. representative spectra
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for s in spectra[:3]:
        ax.plot(s.wavelength, s.flux, lw=0.6, alpha=0.8, label=s.source_id)
    for pair in SKY_WINDOW_PAIRS:
        ax.axvspan(pair.sky.low, pair.sky.high, color="tab:red", alpha=0.15)
    ax.set_xlabel("Wavelength (Angstrom, vacuum)")
    ax.set_ylabel("Flux (1e-17 erg/s/cm^2/Angstrom)")
    ax.set_title("Representative spectra (shaded = sky windows)")
    ax.legend(fontsize=7)
    path = _save(fig, out_dir, "fig01_representative_spectra")
    _sidecar(path, data_kind=data_kind, sample_size=len(spectra[:3]), units="Angstrom vs 1e-17 erg/s/cm^2/A", config_path=config_path)

    # 2. local residual example
    from sdss_sky_residual_quality_audit.continuum import fit_local_continuum
    from sdss_sky_residual_quality_audit.residuals import normalised_residuals
    s0 = spectra[0]
    good = good_pixel_mask(s0.flux, s0.ivar, s0.and_mask)
    fit = fit_local_continuum(s0.wavelength, s0.flux, s0.ivar, good, SKY_WINDOW_PAIRS[0].sky)
    resid = normalised_residuals(s0.wavelength, s0.flux, s0.ivar, good, fit)
    in_plot = (s0.wavelength >= SKY_WINDOW_PAIRS[0].sky.low - 60) & (s0.wavelength <= SKY_WINDOW_PAIRS[0].sky.high + 60)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(s0.wavelength[in_plot], resid[in_plot], lw=0.8, color="tab:blue")
    ax.axvspan(SKY_WINDOW_PAIRS[0].sky.low, SKY_WINDOW_PAIRS[0].sky.high, color="tab:red", alpha=0.15, label="OI 5577 sky window")
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xlabel("Wavelength (Angstrom, vacuum)")
    ax.set_ylabel("Uncertainty-normalised residual")
    ax.set_title(f"Local residual example ({s0.source_id})")
    ax.legend(fontsize=8)
    path = _save(fig, out_dir, "fig02_local_residual_example")
    _sidecar(path, data_kind=data_kind, sample_size=int(np.sum(in_plot)), units="dimensionless residual vs Angstrom", config_path=config_path)

    # 3. scale by region
    labels = [p.label for p in SKY_WINDOW_PAIRS]
    medians = [result.aggregate[label].median_ratio if label in result.aggregate else np.nan for label in labels]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(labels, medians, color="tab:orange")
    ax.axhline(1.0, color="black", ls="--", lw=0.8, label="ratio = 1 (no excess)")
    ax.set_ylabel("Median sky/control residual-scale ratio")
    ax.set_title(f"Scale by region (n={len(spectra)} spectra)")
    ax.tick_params(axis="x", rotation=30)
    ax.legend()
    path = _save(fig, out_dir, "fig03_scale_by_region")
    _sidecar(path, data_kind=data_kind, sample_size=len(spectra), units="dimensionless ratio", config_path=config_path)

    # 4. class comparison
    classes = {s.source_id: s.obj_class for s in spectra}
    groups = stratify_by_class(result.per_spectrum_excess, classes)
    group_labels = sorted(g for g in groups if groups[g])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if group_labels:
        ax.boxplot([[e.ratio for e in groups[g]] for g in group_labels], tick_labels=group_labels)
    ax.axhline(1.0, color="black", ls="--", lw=0.8)
    ax.set_ylabel("Sky/control residual-scale ratio")
    ax.set_title("Class comparison")
    path = _save(fig, out_dir, "fig04_class_comparison")
    _sidecar(path, data_kind=data_kind, sample_size=len(result.per_spectrum_excess), units="dimensionless ratio", config_path=config_path)

    # 5. SNR dependence
    snr = {s.source_id: s.sn_median for s in spectra}
    snr_groups = stratify_by_snr(result.per_spectrum_excess, snr)
    snr_labels = [g for g in ("low_snr", "mid_snr", "high_snr") if snr_groups[g]]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if snr_labels:
        ax.boxplot([[e.ratio for e in snr_groups[g]] for g in snr_labels], tick_labels=snr_labels)
    ax.axhline(1.0, color="black", ls="--", lw=0.8)
    ax.set_ylabel("Sky/control residual-scale ratio")
    ax.set_title("SNR dependence")
    path = _save(fig, out_dir, "fig05_snr_dependence")
    _sidecar(path, data_kind=data_kind, sample_size=sum(len(snr_groups[g]) for g in snr_labels), units="dimensionless ratio", config_path=config_path)

    # 6. null test
    null_pair = build_shifted_null_pair(SKY_WINDOW_PAIRS[0])
    null_excesses = []
    for s in spectra:
        try:
            null_excesses.append(
                evaluate_null_pair(s.source_id, s.wavelength, s.flux, s.ivar,
                                    good_mask=good_pixel_mask(s.flux, s.ivar, s.and_mask), null_pair=null_pair)
            )
        except Exception:  # noqa: BLE001
            continue
    injected_ratios = [e.ratio for e in result.per_spectrum_excess if e.label == SKY_WINDOW_PAIRS[0].label]
    null_ratios = [e.ratio for e in null_excesses]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot([injected_ratios, null_ratios], tick_labels=["OI 5577 sky window", "shifted null (no line)"])
    ax.axhline(1.0, color="black", ls="--", lw=0.8, label="ratio = 1 (no excess)")
    ax.set_ylabel("Residual-scale ratio")
    ax.set_title("Null test (shifted-window control)")
    ax.legend()
    path = _save(fig, out_dir, "fig06_null_test")
    _sidecar(path, data_kind=data_kind, sample_size=len(spectra), units="dimensionless ratio", config_path=config_path)

    print(f"Wrote 6 real-data figures (SVG+PNG+JSON) to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=Path("figures"))
    parser.add_argument("--config", type=Path, default=Path("config/analysis.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    if args.demo:
        plot_demo(demo_series(), args.out_dir / "fig00_smoke_test.png")
        make_demo_figures(args.out_dir, args.config)
        return

    make_real_figures(args.out_dir, args.config, args.manifest, args.raw_dir)


if __name__ == "__main__":
    main()

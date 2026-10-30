"""Reproduce a synthetic paired-window excess-uncertainty diagnostic PNG."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from sdss_sky_residual_quality_audit.paired_window_diagnostics import diagnostic_report

plt.switch_backend("Agg")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/paired_window_robustness.png"))
    args = parser.parse_args()
    report = diagnostic_report()
    med = np.array(report["median_ratio"])
    intervals = np.array(report["bootstrap_95_ratio_interval"])
    yerr = np.vstack((med - intervals[:, 0], intervals[:, 1] - med))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.errorbar(range(len(med)), med, yerr=yerr, fmt="o", capsize=4)
    ax.axhline(1, color="gray", linestyle="--", linewidth=1)
    ax.set(xticks=range(len(med)), xticklabels=report["labels"],
           ylabel="Median sky/control residual-scale ratio",
           title="Seeded synthetic SDSS-window stress test (not observed DR17)")
    ax.tick_params(axis="x", labelrotation=25)
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    plt.close(fig)
    print(args.output)


if __name__ == "__main__":
    main()

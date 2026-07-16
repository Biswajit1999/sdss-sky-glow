"""Deterministic, provenance-recording fetch of real public SDSS DR17 spectra.

Queries the SDSS CasJobs mirror directly via `astroquery.sdss.SDSS`
(astroquery 0.4.7), same access pattern verified in IMPLEMENTATION_PLAN.md
sec.3: `query_sql` for a deterministic class-diverse sample of SpecObj rows,
`get_spectra(matches=...)` to download each spectrum's `spec-*.fits` coadd.
SDSS public data releases (including DR17) require no login and only
acknowledgement of SDSS (https://www.sdss4.org/collaboration/citing-sdss/).

This script performs real network downloads and must only be invoked with
explicit operator authorization for the session, via --i-have-authorization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from sdss_sky_residual_quality_audit.exceptions import ArchiveAccessError
from sdss_sky_residual_quality_audit.fetch import DEFAULT_DATA_RELEASE, build_sample_query, validate_sample_table_columns
from sdss_sky_residual_quality_audit.logging_utils import get_logger
from sdss_sky_residual_quality_audit.provenance import ManifestRow, append_manifest_row, sha256_bytes

LOGGER = get_logger(__name__)

SOURCE_URL = "https://skyserver.sdss.org/dr17/"
LICENCE_TERMS = (
    "SDSS DR17 public data release, open data policy requiring only acknowledgement of SDSS; "
    "https://www.sdss4.org/collaboration/citing-sdss/ (no login/paywall)."
)


def _query_sample(n_rows: int):
    """Run the deterministic SpecObj sample query against SDSS DR17 via astroquery."""
    try:
        from astroquery.sdss import SDSS
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ArchiveAccessError("astroquery is not installed in this environment") from exc

    query = build_sample_query(n_rows)
    try:
        table = SDSS.query_sql(query, data_release=DEFAULT_DATA_RELEASE)
    except Exception as exc:  # noqa: BLE001
        raise ArchiveAccessError(f"SDSS query_sql failed: {exc}") from exc

    if table is None or len(table) == 0:
        raise ArchiveAccessError("SDSS query_sql returned zero rows for the sample query")

    validate_sample_table_columns(list(table.colnames))
    return table


def _download_spectra(table, out_dir: Path) -> list[tuple[str, Path]]:
    """Download `spec-*.fits` files for each row in `table` via SDSS.get_spectra."""
    from astroquery.sdss import SDSS

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        hdulists = SDSS.get_spectra(matches=table, data_release=DEFAULT_DATA_RELEASE)
    except Exception as exc:  # noqa: BLE001
        raise ArchiveAccessError(f"SDSS get_spectra failed: {exc}") from exc

    if not hdulists:
        raise ArchiveAccessError("SDSS get_spectra returned no spectra for the requested sample")

    downloaded: list[tuple[str, Path]] = []
    for row, hdul in zip(table, hdulists):
        source_id = f"spec-{int(row['plate']):04d}-{int(row['mjd']):05d}-{int(row['fiberID']):04d}"
        out_path = out_dir / f"{source_id}.fits"
        hdul.writeto(out_path, overwrite=True)
        downloaded.append((source_id, out_path))
    return downloaded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-spectra", type=int, default=12)
    parser.add_argument("--out-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument(
        "--i-have-authorization",
        action="store_true",
        help=(
            "Required flag confirming the operator has explicitly authorized this "
            "real network download in the current session."
        ),
    )
    args = parser.parse_args()

    if not args.i_have_authorization:
        raise SystemExit(
            "Refusing to download real archive data without --i-have-authorization. "
            "This flag exists so the download only runs after the operator has "
            "explicitly confirmed it in the current session (see docs/DATASET_PLAN.md)."
        )

    table = _query_sample(args.n_spectra)
    LOGGER.info("Selected %d SpecObj rows", len(table))

    downloaded = _download_spectra(table, args.out_dir)
    retrieved_utc = datetime.now(timezone.utc).isoformat()

    for source_id, path in downloaded:
        if not path.is_file():
            raise ArchiveAccessError(f"expected downloaded file missing: {path}")
        data = path.read_bytes()
        digest = sha256_bytes(data)
        size = len(data)
        row = ManifestRow(
            product_id=source_id,
            source="SDSS/DR17",
            source_url=SOURCE_URL,
            retrieved_utc=retrieved_utc,
            sha256=digest,
            file_size_bytes=size,
            selection_reason=(
                f"deterministic sample of {args.n_spectra} SpecObj rows (zWarning=0, snMedian>2, "
                "class in GALAXY/STAR/QSO), ORDER BY specobjid, for sky-residual quality audit"
            ),
            licence_or_terms=LICENCE_TERMS,
        )
        append_manifest_row(args.manifest, row)
        LOGGER.info("Recorded manifest row for %s (%d bytes)", source_id, size)

    print(f"Downloaded and recorded {len(downloaded)} spectra under {args.out_dir}")


if __name__ == "__main__":
    main()

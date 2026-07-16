"""Reusable, testable SDSS archive query/selection helpers.

The actual download-and-manifest orchestration lives in
`scripts/fetch_data.py` (gated behind `--i-have-authorization`); this module
holds the deterministic SQL text and the selection logic so it can be unit
tested without a network connection.

Real-data access plan verified live against astroquery.sdss (astroquery
0.4.7): `SDSS.query_sql`/`query_sql_async` against the DR17 CasJobs mirror,
then `SDSS.get_spectra(matches=<Table>)`. See IMPLEMENTATION_PLAN.md sec.3.
"""
from __future__ import annotations

from sdss_sky_residual_quality_audit.exceptions import ArchiveAccessError

DEFAULT_DATA_RELEASE = 17


def build_sample_query(n_rows: int = 12) -> str:
    """Deterministic SQL SELECT against SpecObj for a small class-diverse sample.

    `zWarning=0` restricts to reliable pipeline redshifts; ordering by
    `specobjid` and capping with `TOP` makes the sample fully reproducible
    across runs against the same DR17 snapshot.
    """
    if n_rows < 1:
        raise ArchiveAccessError("build_sample_query: n_rows must be >= 1")
    return (
        f"SELECT TOP {n_rows} specobjid, plate, mjd, fiberid AS fiberID, run2d, class, subclass, "
        f"z, zWarning, snMedian "
        f"FROM SpecObj "
        f"WHERE zWarning = 0 AND snMedian > 2 "
        f"AND class IN ('GALAXY', 'STAR', 'QSO') "
        f"ORDER BY specobjid"
    )


def validate_sample_table_columns(columns: list[str]) -> None:
    """Raise `ArchiveAccessError` if a query result is missing expected columns."""
    required = {"specobjid", "plate", "mjd", "fiberid", "run2d", "class"}
    have = {c.lower() for c in columns}
    missing = required - have
    if missing:
        raise ArchiveAccessError(f"SDSS query result missing expected columns: {sorted(missing)}")


__all__ = ["DEFAULT_DATA_RELEASE", "build_sample_query", "validate_sample_table_columns"]

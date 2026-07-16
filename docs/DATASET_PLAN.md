# Dataset Plan

## Mode

**real public SDSS spectra**

## Official sources and literature seeds

- Official SDSS spectroscopic data-model documentation
- SDSS DR17 archive documentation
- Ahn et al. BOSS data-release paper, arXiv:1207.7137
- Noll et al. Skycorr, DOI:10.1051/0004-6361/201423908
- Guy et al. DESI spectroscopic pipeline, arXiv:2209.14482

## Acquisition rules

- Prefer official mission/archive endpoints and author-maintained catalogue deposits.
- Record product identifier, query, retrieval UTC, source URL, file size, checksum and licence/terms.
- Do not commit large raw FITS, HDF5 or catalogue files.
- Store a deterministic manifest under `data/manifest.csv`.
- Store only a tiny, clearly labelled synthetic/example dataset in `data/example/`.
- Never replace inaccessible real data with fabricated values while presenting them as observations.

## Required manifest columns

`product_id, source, source_url, retrieved_utc, sha256, file_size_bytes, selection_reason, licence_or_terms`

## FAIR contract

Every derived product must point to the raw product ID, software commit, configuration hash and transformation script.

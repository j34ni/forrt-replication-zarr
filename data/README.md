# `data/` — generated artefacts, never committed

This directory holds the results table produced by the fault-injection harness. **Files in this directory are never committed to git** (`.gitignore` excludes everything except this README — see `data/*` / `!data/README.md`).

## Why there is no download step

This replication does not analyse an external dataset — it tests a structural claim
(Icechunk's atomic metadata+data commit vs. disconnected STAC-style metadata indexes)
via fault injection on **synthetic** Zarr arrays generated on the fly by the harness
(`harness/`). There is nothing to fetch: a user clones the repo, runs
`snakemake --cores 1` (or executes `notebooks/01_atomic_sync.py` directly), and the
notebook drives `harness.run_matrix.run_all()`, which generates the test data,
injects the faults, and writes the results table here.

## What lands here

- `data/results/results.parquet` — one row per (scenario × system × backend × trial),
  with `inconsistent` / `conflict_rejected` columns. Written by
  `harness.run_matrix.run_all()` (called from `notebooks/01_atomic_sync.py`).
  Regenerable from a fresh checkout — never committed; only the summary numbers
  (in `nanopubs/drafts/05_outcome.md`) and the rendered figure
  (`figures/main_result.png`) are.

## Optional MinIO/object-store backend

Running the matrix with `--minio-trials > 0` additionally exercises a real
S3-compatible object store (see `harness/backends.py` and `harness/run_matrix.py`
for the required `MINIO_*` environment variables). This is optional and requires
credentials the harness never stores — export them in your own shell, never paste
them into a chat session.

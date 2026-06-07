# Snakefile — orchestrates the replication pipeline end-to-end.
#
# This replication is a fault-injection harness, not a data-analysis pipeline:
# there is no external dataset to download/clean — the harness (harness/) generates
# synthetic Zarr arrays and injects faults into Icechunk- and STAC-backed stores.
# The whole pipeline therefore lives in one notebook, 01_atomic_sync.py, which
# runs the fault matrix (via harness.run_matrix.run_all), writes the results
# table, and renders the comparison figure.
#
# Usage:
#   snakemake --cores 1                  # run everything
#   snakemake --cores 1 -n               # dry run

NOTEBOOKS = "notebooks"
DATA = "data"
FIGURES = "figures"


rule all:
    input:
        f"{FIGURES}/main_result.png",
        f"{DATA}/results/results.parquet",


# ---------- 01: Atomic synchronization fault-injection matrix + figure ----------
# Runs F1-F3 (and, with MINIO_* env vars set, F1-F4) across Icechunk / STAC B0 / B1,
# writes data/results/results.parquet, and renders figures/main_result.png.
# See harness/run_matrix.py and notebooks/01_atomic_sync.py for the full design.
rule atomic_sync:
    output:
        f"{FIGURES}/main_result.png",
        f"{DATA}/results/results.parquet",
    log:
        "results/logs/01_atomic_sync.log",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 01_atomic_sync.py 2>&1 | tee ../{{log}}"

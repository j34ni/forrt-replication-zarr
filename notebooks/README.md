# `notebooks/` — the replication pipeline

The `.py` file is the **source of truth** (committed, jupytext `py:percent` format,
gitignored `.ipynb` companion regenerated via `jupytext --to notebook --execute`
and embedded in the Jupyter Book — see `myst.yml`).

## This replication is one notebook, not the template's four-stage pipeline

`forrt-replication-template` ships a default `01_data_download` → `02_data_clean` →
`03_analysis` → `04_figures` scaffold for replications that port an external dataset
through a data-analysis pipeline. **This replication doesn't have an external
dataset** — it is a fault-injection test of a structural claim (Icechunk's atomic
metadata+data commit vs. disconnected STAC-style metadata indexes), run against
**synthetic** Zarr arrays generated on the fly. The four-stage scaffold therefore
doesn't fit and was removed; the whole pipeline lives in one notebook:

| File | Role |
|---|---|
| `01_atomic_sync.py` | Runs the fault-injection matrix (`harness.run_matrix.run_all`) across scenarios F1-F4 × systems (Icechunk / STAC B0 / STAC B1) × backends (local filesystem, optionally MinIO/NIRD object store), writes `data/results/results.parquet`, and renders `figures/main_result.png`. |

The Snakefile wraps it in a single `atomic_sync` rule. See the notebook's own
markdown cells for the full experimental design, and `harness/faults.py` /
`harness/run_matrix.py` for the scenario implementations.

## Adding a new notebook

If a future extension to this replication needs another notebook (e.g. an additional
backend comparison or a negative control):

1. Write the jupytext `.py` file in this directory, with a numbered prefix that
   reflects pipeline order.
2. Add it to `myst.yml` TOC as `notebooks/0X_….ipynb` (note: `.ipynb`, not `.py`;
   MyST cannot process `.py`).
3. Add a Snakefile rule that wraps it.
4. The `.github/workflows/jupyter-book.yml` "Execute notebooks" step uses a glob
   (`notebooks/*.ipynb`), so new notebooks are picked up automatically — no workflow
   edit needed.
5. Add every import in the new notebook to `pixi.toml`, then `pixi install` and
   commit the refreshed `pixi.lock`.

## Anti-patterns

- **Don't use `matplotlib.use('Agg')`** — blocks inline display, breaks the Jupyter Book.
- **Don't write absolute paths** — use repo-relative paths so the notebook runs in
  `docker run`, in CI, and locally.
- **Don't claim a notebook works without running it** — see `docs/verify-before-drafting.md`.

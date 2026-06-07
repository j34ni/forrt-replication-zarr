# forrt-replication-zarr

> Does Icechunk's atomic metadata+data commit eliminate the consistency failures
> that plague disconnected STAC-style metadata indexes over object storage? — replication study.
>
> Question-rooted chain (no upstream paper): primary source is the [`zarr-datafusion-search`](https://github.com/developmentseed/zarr-datafusion-search) README by Development Seed.

This repository is a self-contained replication of the headline claim surfaced by the reference source above. It produces:

- A reproducible computational pipeline (Snakefile + notebooks).
- A FORRT-tagged nanopublication chain on the [Science Live platform](https://platform.sciencelive4all.org), documenting the claim, the replication design, and the outcome with full provenance.
- A Zenodo-archived release (source + container image) with a citable DOI.

## Quick start

```bash
git clone https://github.com/j34ni/forrt-replication-zarr.git
cd forrt-replication-zarr
pixi install
pixi run snakemake --cores 1
```

Or with Docker:

```bash
docker run --rm ghcr.io/j34ni/forrt-replication-zarr:latest
```

## Structure

- `paper/` — source-paper PDF dir (unused — this is a question-rooted chain; see `paper/README.md`).
- `notebooks/` — jupytext `.py` notebooks that drive the pipeline.
- `data/` — downloaded by `notebooks/01_data_download.py`, never committed.
- `nanopubs/` — drafts of the FORRT chain field-by-field, plus the published-URI registry.
- `docs/` — operating manuals (FORRT form fields, chain decision tree, claim-type vocabulary).
- `figures/` — curated figures used in the Jupyter Book.

## Nanopublication chain

The published chain is listed in [`nanopubs/PUBLISHED.md`](nanopubs/PUBLISHED.md). Each step links to its viewer URL on the Science Live platform.

## Citation

If you use this work, please cite both:

- This software: [`CITATION.cff`](CITATION.cff) → DOI [{{ZENODO_DOI}}]({{ZENODO_DOI}}).
- The primary source (no DOI — a GitHub README, not a publication): [`zarr-datafusion-search`](https://github.com/developmentseed/zarr-datafusion-search) by Development Seed.

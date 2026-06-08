# forrt-replication-zarr-consistency

## In plain language

**The question:** if you store your array data (Zarr) in one place and keep a
*separate* index describing it (e.g. a STAC catalog) somewhere else, can a reader
ever see the two disagree — say, right after a crash, or when two jobs update the
same dataset at once?

**The answer this replication finds:** with a separate index, yes — we observed it
in all four situations we tested. With **Icechunk**, which writes the array data and
its metadata together in a single atomic transaction, no — it was never observed
inconsistent, in any of the four situations, including on real cloud object storage.

**At a glance — what breaks, and where:**

| What happens | Separate index (STAC/JSON + Zarr) | Icechunk |
|---|---|---|
| Crash mid-update (data written, catalog not yet) | ❌ catalog describes the wrong data, until a cleanup job runs | ✅ nothing changes until the update fully completes |
| Crash mid-update (catalog written, data not yet) | ❌ catalog points at data that isn't there | ✅ all-or-nothing — this failure mode doesn't exist |
| A reader arrives mid-update | ❌ can see a half-updated mix | ✅ always sees the last fully-committed version |
| Two jobs write the same data at once | ❌ one silently overwrites the other | ✅ the store rejects the second write — no silent loss |

> **Should you use Icechunk?** If your datasets are written once and never changed, a
> separate metadata index is fine — there's nothing that can get out of sync. But if
> they're *updated over time* — and especially if more than one process can write —
> a disconnected index can be caught in an inconsistent state, and avoiding that takes
> extra machinery you'd have to build and maintain yourself. A transactional store
> like Icechunk gives you that safety by construction: in our tests it was never
> observed inconsistent, across all four situations, on real cloud object storage.
>
> **The one caveat that matters:** this depends on the underlying object store
> supporting **conditional writes** — informally, "refuse a write if someone else
> changed the data first," the same idea as a wiki refusing to save your edit because
> someone else's landed first (also called *compare-and-swap*, or CAS). Icechunk's
> guarantee is only as strong as that. We confirmed it holds on NIRD/Sigma2; other
> S3-compatible providers should behave the same, but weren't tested here.

The full plain-language walkthrough — what F1–F4 mean as everyday stories, how to
read the results figure, and the technical replication design — is in
[`notebooks/01_atomic_sync.py`](notebooks/01_atomic_sync.py) (rendered as the first
notebook in this Jupyter Book's table of contents).

**The headline result, in one figure:**

![Metadata–data inconsistency under fault injection — Icechunk vs STAC, across F1-F4 on both a local filesystem and a real NIRD/Sigma2 S3-compatible object store. Icechunk stays at zero in every panel; both STAC variants land at N (every trial inconsistent) wherever they're exercised.](figures/main_result.png)

**Where this figure comes from, and why you might see a different one in the notebook
below:** that notebook, `notebooks/01_atomic_sync.py`, is what produces it — but the
4-panel version above (panels 1-3 on the local filesystem, panel 4 the NIRD/Sigma2
object-store run that the "confirmed it holds on NIRD/Sigma2" claim rests on) only
renders when the notebook is run with live `MINIO_*` credentials for a real
S3-compatible endpoint (see `data/README.md` for how to set those up; never paste them
into a chat session). As rendered in this book, the notebook ran without those
credentials, so its own output below shows only the three locally-reproducible panels
(F1-F3, saved separately to `figures/main_result_local_only.png` so a credential-less
run can never overwrite the evidence above). The figure above is the one committed at
`figures/main_result.png`, described in full in
[`nanopubs/drafts/05_outcome.md`](nanopubs/drafts/05_outcome.md).

---

> **Replication framing:** does Icechunk's atomic metadata+data commit eliminate the
> consistency failures that plague disconnected STAC-style metadata indexes over
> object storage? Question-rooted chain (no upstream paper): the primary source is the
> [`zarr-datafusion-search`](https://github.com/developmentseed/zarr-datafusion-search)
> README by Development Seed.

This repository is a self-contained replication of the headline claim surfaced by the reference source above. It produces:

- A reproducible computational pipeline (Snakefile + notebooks).
- A FORRT-tagged nanopublication chain on the [Science Live platform](https://platform.sciencelive4all.org), documenting the claim, the replication design, and the outcome with full provenance.
- A Zenodo-archived release (source + container image) with a citable DOI.

## Quick start

```bash
git clone https://github.com/j34ni/forrt-replication-zarr-consistency.git
cd forrt-replication-zarr-consistency
pixi install
pixi run snakemake --cores 1
```

Or with Docker:

```bash
docker run --rm ghcr.io/j34ni/forrt-replication-zarr-consistency:latest
```

## Structure

- `paper/` — source-paper PDF dir (unused — this is a question-rooted chain; see `paper/README.md`).
- `notebooks/` — jupytext `.py` notebooks that drive the pipeline.
- `data/` — generated by `notebooks/01_atomic_sync.py` (synthetic test data + results table), never committed.
- `nanopubs/` — drafts of the FORRT chain field-by-field, plus the published-URI registry.
- `docs/` — operating manuals (FORRT form fields, chain decision tree, claim-type vocabulary).
- `figures/` — curated figures used in the Jupyter Book.

## Nanopublication chain

The published chain is listed in [`nanopubs/PUBLISHED.md`](nanopubs/PUBLISHED.md). Each step links to its viewer URL on the Science Live platform.

## Citation

If you use this work, please cite both:

- This software: [`CITATION.cff`](CITATION.cff) → DOI [10.5281/zenodo.20596857](https://doi.org/10.5281/zenodo.20596857).
- The primary source (no DOI — a GitHub README, not a publication): [`zarr-datafusion-search`](https://github.com/developmentseed/zarr-datafusion-search) by Development Seed.

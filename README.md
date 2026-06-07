# forrt-replication-zarr-consistency

[![CI](https://github.com/j34ni/forrt-replication-zarr-consistency/actions/workflows/ci.yml/badge.svg)](https://github.com/j34ni/forrt-replication-zarr-consistency/actions/workflows/ci.yml)
[![Jupyter Book](https://github.com/j34ni/forrt-replication-zarr-consistency/actions/workflows/jupyter-book.yml/badge.svg)](https://j34ni.github.io/forrt-replication-zarr-consistency/)
[![Docker](https://github.com/j34ni/forrt-replication-zarr-consistency/actions/workflows/docker.yml/badge.svg)](https://github.com/j34ni/forrt-replication-zarr-consistency/pkgs/container/forrt-replication-zarr-consistency)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/DOI/{{ZENODO_DOI}}.svg)]({{ZENODO_DOI}})
[![FAIR4RS](https://img.shields.io/badge/FAIR4RS-conformant-brightgreen)](docs/fair4rs-checklist.md)
[![FORRT](https://img.shields.io/badge/FORRT-replication-blue)](https://forrt.org/)
[![Science Live](https://img.shields.io/badge/Science%20Live-nanopub%20chain-purple)](nanopubs/PUBLISHED.md)
[![RO-Crate](https://img.shields.io/badge/RO--Crate-1.2-orange)](ro-crate-metadata.json)

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

<details>
<summary><b>The fuller walkthrough, in plain language</b> (click to expand)</summary>

### The claim being tested

There's a common pattern in Earth-data systems: you store your big array data (Zarr)
in object storage, and you keep the *metadata about it* in a separate index — a STAC
catalog, CMR, etc. The data lives in one place, the description of it in another. The
claim — from a [Development Seed prototype](https://github.com/developmentseed/zarr-datafusion-search),
relaying an Earthmover whitepaper — is that those disconnected metadata stores are
fragile (keeping the index and the data in sync takes "complex, fragile orchestration,"
and they can drift apart), and that Icechunk fixes this by writing the data *and* its
metadata together in a single atomic transaction. In one sentence: *a transactional
store (Icechunk) prevents the data/metadata inconsistency that a disconnected index
(STAC) is exposed to.* That sentence is what this repo tests. (This is an industry
claim with no published benchmark — "replicating" it means building an independent
test from scratch and checking whether the property holds.)

### How the test works

The trick is making "inconsistency" measurable. Alongside each dataset we store a
**checksum of the data** as its own metadata. The rule: the checksum recorded in the
metadata must equal the checksum you get by re-reading the actual data — if they
disagree, the store is observably inconsistent. We compare **Icechunk** (data +
metadata committed together, atomically) against a **disconnected STAC index** (write
the data, then *separately* write a JSON file with the checksum — two writes, not
atomic), and subject both to four things that go wrong in practice — see the
"real-world story" column in [`notebooks/01_atomic_sync.py`](notebooks/01_atomic_sync.py)
for what F1–F4 actually mean. Each scenario runs many times, on a local disk and on a
real cloud object store (NIRD/Sigma2).

### What we found

- **Icechunk was never observed inconsistent** — zero, across all four situations, on
  both backends.
- **The disconnected index was** — always, in the naive case; even the best-effort
  version couldn't close the "reader arrives mid-update" window (see the F1 panel's
  caption in the notebook for what that window actually means).
- **The decisive test was two writers racing on real cloud storage:** every stale
  write was rejected (100/100 trials) instead of silently overwriting. That's what
  proves the guarantee holds on object storage — the store enforces *conditional
  writes*.

(We tested *only* the consistency claim. The prototype's other selling point — query
performance via DataFusion — is a separate question we didn't touch.)

</details>

---

> **Replication framing:** does Icechunk's atomic metadata+data commit eliminate the
> consistency failures that plague disconnected STAC-style metadata indexes over
> object storage? Question-rooted chain (no upstream paper): the primary source is the
> [`zarr-datafusion-search`](https://github.com/developmentseed/zarr-datafusion-search)
> README by Development Seed.

This is a self-contained replication of the headline claim surfaced by the reference source above. It produces a reproducible fault-injection pipeline, a Zenodo-archived release with a citable DOI, and a FORRT-tagged nanopublication chain on the [Science Live platform](https://platform.sciencelive4all.org).

---

## Quick start

```bash
git clone https://github.com/j34ni/forrt-replication-zarr-consistency.git
cd forrt-replication-zarr-consistency
pixi install
pixi run snakemake --cores 1
```

(Pixi resolves `pixi.toml` against the per-platform `pixi.lock`, installs the env under `.pixi/`, and provides `pixi run` for any task without needing an `activate` step.)

Or with Docker:

```bash
docker run --rm ghcr.io/j34ni/forrt-replication-zarr-consistency:latest
```

The Jupyter Book version is at <https://j34ni.github.io/forrt-replication-zarr-consistency/>.

## Built from a template

This repository was created from [`sciencelivehub/forrt-replication-template`](https://github.com/sciencelivehub/forrt-replication-template). The template ships an operating manual for AI assistants ([`CLAUDE.md`](CLAUDE.md), [`AGENTS.md`](AGENTS.md)), domain conventions ([`DOMAIN.md`](DOMAIN.md)), and reference docs (`docs/`) so that an AI working only inside this repository can guide a researcher from "paper PDF + GitHub repo" to "published FORRT chain + Zenodo DOI" with no other context.

If you are reading this in a fresh fork, run [`/init-template`](.claude/skills/init-template/SKILL.md) inside Claude Code to substitute the placeholder tokens with your details. (For other AI tools, see [`docs/ai-portability.md`](docs/ai-portability.md).)

After `/init-template`, do these one-time setup steps to enable the full CI/CD path:

- **Enable GitHub Pages** at *Settings → Pages → Source: GitHub Actions*. Until enabled, the Jupyter Book build runs but the deploy step is skipped (CI stays green).
- The CI workflows ship with **scaffold-detection guards** — they run end-to-end only after you implement Phase 2 (the `notebooks/*.py` files). Until then they exit early with an informative `::notice::` and the badges stay green.

## Repository structure

```
.
├── CLAUDE.md / AGENTS.md       # operating manual for AI assistants
├── DOMAIN.md                   # domain flavour (current: biodiversity + earth observation)
├── USER_PREFERENCES.md         # per-user style (edit on first clone)
├── README.md                   # this file
├── LICENSE                     # MIT
├── CITATION.cff                # how to cite
├── codemeta.json               # software metadata (CodeMeta-2.0)
├── ro-crate-metadata.json      # research object packaging (RO-Crate 1.2)
├── pixi.toml + pixi.lock       # pinned dependencies (single source of truth; lockfile is per-platform)
├── Dockerfile                  # container build
├── Snakefile                   # pipeline orchestration
├── myst.yml + index.md         # Jupyter Book scaffold
├── paper/                      # source-paper PDF dir (unused — question-rooted chain, see paper/README.md)
├── data/                       # downloaded artefacts (gitignored)
├── notebooks/                  # jupytext .py pipeline (single fault-injection notebook — see notebooks/README.md)
├── nanopubs/                   # FORRT chain drafts + published-URI registry
├── docs/                       # reference material
├── figures/                    # curated figures used in the Jupyter Book
├── .github/workflows/          # CI, Jupyter Book, Docker
└── .claude/                    # Claude Code agents, skills, sandbox config
```

## What you get

This template bakes in conventions that took multiple replications to discover. By using it, you inherit:

- **FAIR4RS conformance** — see [`docs/fair4rs-checklist.md`](docs/fair4rs-checklist.md) for the principle-by-principle mapping.
- **Self-contained data downloads** — the first notebook fetches everything; no manual data prep.
- **`pixi.toml` + `pixi.lock` as single source of truth** — local dev, Docker, and CI all install the same per-platform-pinned env.
- **`prefix-dev/setup-pixi`-based CI** — caches the env, runs the pipeline with `pixi run`, executes notebooks via a glob, fails fast on a stale lockfile.
- **Jupyter Book deployment** — auto-deploys to GitHub Pages with `BASE_URL` set correctly. (Don't put `base_url` in `myst.yml` — MyST silently ignores it.)
- **Docker + GHCR + Zenodo image archival** — `release` trigger pushes to GHCR and (optionally) archives to Zenodo for long-term preservation.
- **RO-Crate packaging** — the entire repo is a navigable Research Object via `ro-crate-metadata.json` (Process Run Crate + Workflow RO-Crate profiles).
- **Six-step FORRT chain workspace** — `nanopubs/drafts/` has a field-by-field skeleton for each step. `nanopubs/PUBLISHED.md` is the URI registry.
- **Layered AI guidance** — `CLAUDE.md` (universal) + `DOMAIN.md` (swappable per field) + `USER_PREFERENCES.md` (per-user). See [`docs/ai-portability.md`](docs/ai-portability.md) for non-Claude AI tools.
- **Sandbox by default** — `.claude/settings.json` denies file ops outside the repo, so a fresh AI session can't accidentally read `~/.ssh/` or write to `/etc/`.

## The six FORRT chain steps

A complete FORRT chain has six steps published on [platform.sciencelive4all.org](https://platform.sciencelive4all.org):

```
Quote-with-comment  →  AIDA  →  FORRT Claim  →  Replication Study  →  Replication Outcome  →  CiTO Citation
```

(For question-rooted chains with no upstream paper, replace step 1 with PICO or PCC. See [`docs/chain-decision-tree.md`](docs/chain-decision-tree.md).)

Drafts live in [`nanopubs/drafts/`](nanopubs/drafts/) field-by-field. Published URIs go into [`nanopubs/PUBLISHED.md`](nanopubs/PUBLISHED.md).

Optional further layers:

- **Research Software nanopub** — for reusable upstream tools (not demo repos). See [`docs/forrt-form-fields.md`](docs/forrt-form-fields.md) § Research Software.
- **Research Synthesis nanopub** — when this chain is part of a multi-chain story. See [`docs/forrt-form-fields.md`](docs/forrt-form-fields.md) § Research Synthesis.

## After publishing

When the chain is live and the FAIR4RS checklist is green, drafting an announcement post is the next step. See [`docs/announcement-template.md`](docs/announcement-template.md) for the structural template (vision-piece-first; the worked replication is the payoff, not the lead).

For lower-level nanopub work — retraction, superseding, batch publishing — see [`docs/programmatic-nanopubs.md`](docs/programmatic-nanopubs.md).

## Citation

If you use this work, please cite both:

- This software: [`CITATION.cff`](CITATION.cff) → DOI [{{ZENODO_DOI}}]({{ZENODO_DOI}})
- The primary source (no DOI — a GitHub README, not a publication): [`zarr-datafusion-search`](https://github.com/developmentseed/zarr-datafusion-search) by Development Seed

## Acknowledgements

This repository was built from [`sciencelivehub/forrt-replication-template`](https://github.com/sciencelivehub/forrt-replication-template), part of the [Science Live platform](https://platform.sciencelive4all.org). The template is licensed MIT and contributions (especially new domain flavours under [`docs/domain-flavours/`](docs/domain-flavours/)) are welcome.

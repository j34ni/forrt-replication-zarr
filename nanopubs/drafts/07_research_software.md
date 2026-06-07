# 07 — Research Software

**Form heading:** *"Research Software — Describe research software with metadata including repository, supporting publications, and related resources."*

> **Scope check (passed):** the fault-injection harness (`harness/`) is a reusable
> software artefact — it tests the atomicity guarantee of any Icechunk-backed store
> against any disconnected STAC baseline, and can be reused by other replications or
> adapted to different backends. It is NOT a one-off demo repo. Icechunk and STAC
> themselves are not our software — this nanopub is for the harness only.
>
> This nanopub is published AFTER the FORRT chain (steps 01–06) and one-way cites the
> Claim URI. It does not appear in the chain itself.

---

## Field-by-field draft

### URI of published software (text input, required)

Zenodo concept DOI URL once minted (Phase 4); use GitHub URL until then.

```
https://github.com/j34ni/forrt-replication-zarr-consistency
```

> Update to `https://doi.org/<zenodo-concept-doi>` after Phase 4 release.

### Software Title (text input, required)

```
zarr-icechunk-atomicity-harness — fault-injection consistency test suite for Icechunk vs STAC
```

### Repository URL (text input, required)

```
https://github.com/j34ni/forrt-replication-zarr-consistency
```

### Research Project (text input, optional)

URI of the FORRT Claim (step 03) — the back-link from this software to the chain.
Pull from `nanopubs/PUBLISHED.md` after publishing step 03.

```
TBD — paste Claim URI after publishing step 03
```

### License (text input, optional)

```
https://spdx.org/licenses/MIT.html
```

### Related Datasets (repeatable group, optional)

*(skip — optional: the harness generates synthetic data; no external dataset DOIs)*

### Related Publications (repeatable group, optional)

One-way back-links to the chain this software implements.

- Item 1 (FORRT Outcome URI, step 05): `TBD — paste after publishing step 05`
- Item 2 (Development Seed prototype — cited work): `https://github.com/developmentseed/zarr-datafusion-search`

---

## Publication note

Publish this AFTER steps 01–06 are complete and their URIs are in `nanopubs/PUBLISHED.md`.
Paste the resulting URI into `nanopubs/PUBLISHED.md` step 07.

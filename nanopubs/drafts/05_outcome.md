# 05 — FORRT Replication Outcome

**Form heading:** *"FORRT Replication Outcome — Record the outcome of a replication study."*

> All numbers in this draft are read directly from `data/results/results.parquet`,
> produced by running `python -m harness.run_matrix --trials 1000` (icechunk 2.0.6,
> zarr 3.2.1, local filesystem backend, seed=42). Do not edit these numbers without
> re-running the matrix.

---

## Field-by-field draft

### Short URI suffix for outcome ID (text input, required)

```
icechunk-atomicity-outcome-2026
```

### Plain-text label for the outcome (text input, required)

```
Icechunk atomic commit: zero inconsistencies across F1/F2/F3, local filesystem backend
```

### Search for a FORRT replication study (search/select, required)

URI of the Replication Study published in step 04. Pull from `nanopubs/PUBLISHED.md`.

```
TBD — paste Study URI after publishing step 04
```

### Repository URL (text input, required)

```
https://github.com/j34ni/forrt-replication-zarr
```

### Completion date (date picker, required)

```
2026-06-07
```

### Validation status (dropdown, required)

- [ ] Validated
- [x] PartiallySupported
- [ ] Contradicted
- [ ] Inconclusive
- [ ] NotTested

> **Rationale:** The Icechunk side of the claim is confirmed on the local filesystem
> backend (0/1000 across F1/F2/F3). The baseline asymmetry is real (STAC B0 = 1000/1000;
> B1 closes F2 and the post-sweep F1 window but not F3). However, local filesystem is
> the easiest backend — Icechunk's atomicity guarantee on object stores depends on
> conditional writes (compare-and-swap), which is only exercised on MinIO and real S3.
> The claim is about those production backends; local FS validates the mechanism but not
> the claim in its target environment. PartiallySupported is the honest status until
> the MinIO / real S3 matrix is complete.
>
> CiTO intention for step 06: `qualifies` (PartiallySupported → qualifies).
> Update to `confirms` after the object-store backends are run and reproduce the result.

### Confidence level (dropdown, required)

- [ ] VeryHighConfidence
- [ ] HighConfidence
- [x] Moderate
- [ ] LowConfidence
- [ ] VeryLowConfidence

> **Rationale:** The local-FS results are internally consistent and deterministic, but
> the fault scenarios are all deterministic (not probabilistic) and the claim's target
> environment (object stores with conditional writes) has not been tested. Moderate
> reflects strong local evidence with a meaningful untested gap.

### Describe the overall conclusion about the original claim (textarea, required)

```
On the local filesystem backend, Icechunk's atomic commit produces zero observable
metadata–data inconsistencies across all three core fault scenarios in 1000 independent
trials. A naive disconnected STAC index (B0) produces inconsistencies in every trial
across all scenarios. STAC B1 (best-effort: write-ordering + reconciliation sweeper)
eliminates the F2 scenario by construction and closes the F1 window after the sweeper
runs, but cannot prevent the F3 concurrent-read window — any reader arriving between
the zarr write and the STAC update observes an inconsistency, identical to B0.

These results partially support the claim. The mechanism (atomic commit vs disconnected
write) behaves as asserted on local filesystem. However, Icechunk's guarantee on object
stores depends on conditional writes (compare-and-swap), which local filesystem does not
exercise. The claim earns its full weight only once MinIO and real S3 are in the matrix.
```

### Describe the evidence that supports your conclusion (textarea, required)

```
Fault-injection harness, 1000 trials per scenario per system, local filesystem backend.
icechunk 2.0.6, zarr 3.2.1, Python 3.12. Results in data/results/results.parquet.
All fault scenarios are deterministic (fault always injected at the same point);
counts reflect worst-case presence of inconsistency, not empirical hit probability.

F1 — crash after data write, before metadata update:
  Icechunk:   0/1000 inconsistencies (0 percentage points)
              [abandoned session; last committed snapshot unchanged]
  STAC B0: 1000/1000 (100 percentage points)
              [zarr updated, STAC JSON not — stale metadata persists]
  STAC B1: 1000/1000 pre-sweep → 0/1000 post-sweep
              [write-ordering does not prevent F1; sweeper detects and corrects
               the mismatch by recomputing sha256 from zarr and overwriting STAC]

F2 — crash after metadata update, before data write:
  Icechunk:   0/1000 (not applicable — single-session atomicity prevents F2 by
              construction; recorded as 0, not measured)
  STAC B0: 1000/1000 (100 percentage points)
              [STAC updated with new sha256, zarr still holds old data]
  STAC B1:    0/1000 (by design — write-ordering enforces data-before-STAC, making
              the F2 fault point unreachable in B1's code path; not empirically
              measured — asserted by inspection of the implementation)

F3 — concurrent reader during in-progress write:
  Icechunk:   0/1000 (readonly_session reads last committed snapshot;
              in-progress writer changes are invisible until commit)
  STAC B0: 1000/1000 (100 percentage points)
  STAC B1: 1000/1000 (100 percentage points)
              [write-ordering does not close the F3 window; the sweeper was not
               invoked during F3 trials because post-hoc reconciliation cannot
               retroactively prevent a reader that already observed the window]

Note: F3 counts represent worst-case exposure (simulated reader always arrives
between the two writes). In a real workload, hit probability depends on window
duration and reader polling frequency — not measured here.
```

### Describe what limits the conclusions of the study (textarea, optional)

```
Backend scope — most important limitation: local filesystem only. Icechunk's atomicity
on object stores requires conditional writes (compare-and-swap) and strong
read-after-write consistency. Local filesystem provides these trivially (POSIX rename
is atomic); MinIO and real S3 are where the guarantee must actually be verified against
the object-store implementation. Results on those backends may differ. This study
validates the mechanism on the easy path; it does not validate the claim in its target
production environment.

Deterministic fault injection: all fault scenarios place the fault or the simulated
reader at a fixed point in the write sequence. The 1000/1000 counts for STAC B0/B1 F3
reflect "the inconsistency window always exists" — they do not measure how often a
real concurrent reader would hit that window in practice. Probabilistic fault injection
(randomised fault timing relative to write progress) is deferred to a follow-on run.

F2 B1 = 0 by design, not measurement: B1's write-ordering makes the F2 fault point
unreachable in the implementation. The zero is an assertion from code inspection, not
an empirical result from running the scenario.

Synthetic data only: 256 float32 values per array. Real L2 EO granule sizes may
produce wider F3 windows (more data to write = longer gap between zarr write and STAC
update), which would increase real-world hit probability but would not change the
binary presence/absence result.

F3 staleness window duration not measured — only presence or absence of inconsistency
recorded. Quantifying the window requires a concurrent-thread reader design.

F4–F6 (concurrent competing writers, partial batch failure) are out of scope for this
initial vertical slice.

Icechunk 2.0.6 warns that the local filesystem store is "not safe for concurrent
commits." Our scenarios involve a single writer at a time (F1/F2/F3), so this does not
affect the reported results — but it reinforces that local FS is not a production
backend.
```

---

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 05.
Use that URI in `06_citation.md` field "Identifier for the citing creative work".

> **Before publishing:** if MinIO / real S3 results are available and reproduce the
> local-FS finding, upgrade Validation status to Validated, Confidence to
> HighConfidence, and CiTO intention to `confirms`. Update the conclusion and evidence
> fields accordingly.

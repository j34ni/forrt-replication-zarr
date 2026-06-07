# 05 — FORRT Replication Outcome

**Form heading:** *"FORRT Replication Outcome — Record the outcome of a replication study."*

> All numbers in this draft are read directly from `data/results/results.parquet`
> (10400 rows), produced by `python -m harness.run_matrix --trials 1000 --minio-trials 100`
> (icechunk 2.0.6, zarr 3.2.1, seed=42). The matrix covers two backends: local filesystem
> (1000 trials × F1/F2/F3/F4 × {icechunk, stac_b0, stac_b1} — STAC baselines are not
> exercised under F4, which is Icechunk-specific) and a real object-store backend — NIRD/Sigma2
> S3-compatible storage (`s3.nird.sigma2.no`, bucket `jeani-ns1000k-grid4earth`, 100 trials ×
> F1/F2/F3/F4, Icechunk only — the STAC baseline result is backend-agnostic by construction;
> see `harness/run_matrix.py`). Do not edit these numbers without re-running the matrix.
>
> **2026-06-07 history note (two corrections in one day — both kept here for the audit
> trail):**
> 1. An early draft of this Outcome upgraded the status to Validated on the strength of
>    the NIRD/Sigma2 F1/F2/F3 run alone. On review, F1/F2/F3 as implemented do not
>    exercise Icechunk's conditional-write (compare-and-swap) path — they test the
>    session commit-or-abandon model and snapshot isolation, which are structural
>    properties of the session API that hold regardless of the storage layer's CAS
>    support (see the Validation status rationale below for the full argument). That
>    upgrade was reverted to PartiallySupported, and a fourth scenario — F4, concurrent
>    racing writers, the scenario that actually contests the branch tip — was implemented
>    and unit-tested locally (20/20 pass) but **not yet run against NIRD/Sigma2**.
> 2. F4 has now been run for real against NIRD/Sigma2 with live `MINIO_*` credentials:
>    **100/100 trials show `conflict_rejected == True` and `inconsistent == False`** — the
>    positive control is green, on the actual target backend, with measured (not asserted,
>    not unit-test-only) results. That is the evidence the first correction said would be
>    required before re-upgrading. This draft now reflects that upgrade — to Validated /
>    HighConfidence / `confirms` — grounded specifically in F4, not in F1-F3.

---

## Field-by-field draft

### Short URI suffix for outcome ID (text input, required)

```
icechunk-atomicity-outcome-2026
```

### Plain-text label for the outcome (text input, required)

```
Icechunk atomic commit: zero inconsistencies across F1-F4, including a positive control for conditional-write rejection (F4), on local filesystem and on a real S3-compatible object store (NIRD)
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

- [x] Validated
- [ ] PartiallySupported
- [ ] Contradicted
- [ ] Inconclusive
- [ ] NotTested

> **Rationale:** Icechunk's atomicity-on-object-stores claim rests on **conditional
> writes (compare-and-swap on the branch tip)**: the property that lets the store
> reject a commit whose session is based on a stale tip — the part of the claim that is
> *specific* to object stores (local filesystem gets atomicity "for free" via POSIX
> rename; an object store must implement CAS deliberately). F1/F2/F3 do not exercise
> that path:
>   - **F1** abandons a session before any commit is attempted — no conditional write
>     is ever issued. This passes on any backend; it tests the commit-or-abandon model.
>   - **F2** is not applicable to Icechunk by construction (single-session co-commit).
>   - **F3** has exactly one writer and one reader — the CAS precondition is never
>     contested, because there is no second writer to race against.
> Their success on NIRD (0/100 inconsistencies, identical to local FS) is real and
> worth reporting — it shows the session-model guarantees reproduce identically on a
> production object store — but, as this Outcome's own earlier (and reverted) Validated
> upgrade incorrectly assumed, it is *structural*: a property of the session API, not of
> NIRD's conditional-write implementation specifically.
>
> The scenario that actually depends on CAS is **F4 — concurrent racing writers**: two
> sessions branch from the same committed tip, edit the *same* region, and race to
> commit; the store must reject the loser's stale-tip commit with a conflict. F4
> (`harness/faults.py::f4_icechunk_racing_writers`,
> `harness/baseline_icechunk.py::icechunk_racing_writers`) has now been run for real
> against NIRD/Sigma2 with live `MINIO_*` credentials — not just unit-tested locally:
>
>   - **NIRD/Sigma2 (100 trials, the target environment):** `conflict_rejected == True`
>     in 100/100 trials — every stale-tip commit was rejected with `icechunk.ConflictError`
>     — and `inconsistent == False` in 100/100 — the store never ended in a mixed state,
>     regardless of which writer won. This is the positive control, green, on the actual
>     backend the claim is about.
>   - **Local filesystem (1000 trials, sanity comparison):** identical pattern,
>     `conflict_rejected == True` in 1000/1000, `inconsistent == False` in 1000/1000 —
>     expected, since POSIX rename also enforces a form of CAS, and confirms the harness
>     measures what it claims to measure.
>
> This is the evidence this Outcome's own prior correction said would be required:
> "Once F4 shows 'first commit wins, stale commit rejected, store consistent' across the
> NIRD trials — with the positive control green — that's the evidence that earns
> Validated." It now exists, measured, on the real object store. Combined with the
> session-model results (F1/F2/F3, 0 inconsistencies on both backends), every sub-claim
> in the headline claim — commit-or-abandon atomicity, snapshot isolation, *and*
> conditional-write CAS on a real S3-compatible object store — is now supported by
> measured evidence in its target environment. Validated is the honest status.
>
> CiTO intention for step 06: `confirms` (Validated → confirms).

### Confidence level (dropdown, required)

- [ ] VeryHighConfidence
- [x] HighConfidence
- [ ] Moderate
- [ ] LowConfidence
- [ ] VeryLowConfidence

> **Rationale:** Every sub-claim — commit-or-abandon atomicity, snapshot isolation, and
> conditional-write CAS — is now tested thoroughly and deterministically on two backends,
> with internally consistent, reproducible, measured results: F1/F2/F3 at 1000 (local) +
> 100 (NIRD) trials, F4 at 1000 (local) + 100 (NIRD) trials. The result that mattered most
> — F4's positive control on the real object store — came back unambiguously green
> (100/100 `conflict_rejected`, 0/100 `inconsistent`), with no partial or borderline cases
> to weigh. Not VeryHighConfidence: the NIRD sample (100 trials) is an order of magnitude
> smaller than the local-FS sweep (1000), a single object-store provider was tested, and
> the harness uses deterministic (not randomised-timing) fault injection — see
> Limitations. Those are the residual reasons to keep this at HighConfidence rather than
> VeryHigh, not gaps in *which* sub-claims were tested.

### Describe the overall conclusion about the original claim (textarea, required)

```
Icechunk's session commit-or-abandon model and snapshot isolation produce zero observable
metadata–data inconsistencies across F1 (crash after data, before metadata — abandoned
session), F2 (metadata-ahead-of-data state, measured directly — not applicable as a fault
*injection* since Icechunk co-commits both in one session, but now empirically checked
rather than asserted), and F3 (concurrent reader during an in-progress write), on both
backends tested: 0/1000 trials on the local filesystem, and 0/100 trials on a real
S3-compatible object store (NIRD/Sigma2, `s3.nird.sigma2.no`). A naive disconnected STAC
index (B0) produces inconsistencies in every trial across all scenarios on the local
filesystem. STAC B1 (best-effort: write-ordering + reconciliation sweeper) eliminates the
F2 scenario by construction and closes the F1 window after the sweeper runs (1000 → 0),
but cannot prevent the F3 concurrent-read window — any reader arriving between the zarr
write and the STAC update observes an inconsistency, identical to B0.

Beyond the session-model scenarios, a fourth scenario — F4, concurrent racing writers —
tests the mechanism the claim attributes *specifically* to object stores: conditional
writes (compare-and-swap on the branch tip), the property that lets a store reject a
commit whose session is based on a stale tip. Two sessions branch from the same committed
snapshot, write OVERLAPPING data to the same array region (forcing a genuine conflict —
Icechunk can silently rebase non-overlapping edits, which would not test rejection), and
both attempt to commit. F4 was run on both backends — local filesystem (1000 trials) and
NIRD/Sigma2 (100 trials, with live `MINIO_*` credentials) — and on **both**, every single
trial showed: the first commit succeeds and moves the branch tip; the second session,
based on a now-stale tip, has its commit rejected with `icechunk.ConflictError` (the exact
exception, confirmed against the installed icechunk==2.0.6 API/docstring); and the store
ends in a single coherent state regardless of which writer won.

  F4 — conflict_rejected == True / inconsistent == False:
    Local filesystem:        1000/1000 / 1000/1000
    NIRD/Sigma2 object store:  100/100 /   100/100

This is the positive control for the conditional-write guarantee, green, on the actual
target backend — measured with real network round-trips against a production
S3-compatible object store, not asserted from code or inferred from a local unit test.

Taken together, every sub-claim in the headline claim is now supported by measured
evidence in its target environment: commit-or-abandon atomicity (F1), snapshot isolation
(F3), the absence of a metadata-ahead-of-data state (F2, measured), and — the part that
is *specific* to object stores and the reason this replication went to NIRD — conditional
writes correctly enforcing atomicity under a genuine write race (F4). The claim is
Validated.
```

### Describe the evidence that supports your conclusion (textarea, required)

```
Fault-injection harness, run on two backends. icechunk 2.0.6, zarr 3.2.1, Python 3.12.
Results in data/results/results.parquet (10400 rows total). All fault scenarios are
deterministic (fault always injected at the same point, or — for F4 — the same race is
forced deliberately every trial); counts reflect worst-case presence of inconsistency,
not empirical hit probability.

  Backend 1 — local filesystem: 1000 trials per scenario per system for F1/F2/F3
  (icechunk, stac_b0, stac_b1) and 1000 trials of F4 (icechunk only), seed=42.
  Backend 2 — NIRD/Sigma2 S3-compatible object store (`s3.nird.sigma2.no`, bucket
  `jeani-ns1000k-grid4earth`, prefix `icechunk-atomicity-test/<run_id>/`): 100 trials per
  scenario for F1/F2/F3/F4, Icechunk only, seed=43. (The STAC baseline is not re-run on
  the object store: its inconsistency is a structural property of the disconnected
  two-step write, not of the storage layer — see `harness/run_matrix.py` for the
  rationale. F4 is Icechunk-specific by construction — STAC has no commit/conflict model
  to race against.)

=== Local filesystem backend (1000 trials) ===

F1 — crash after data write, before metadata update:
  Icechunk:   0/1000 inconsistencies (0 percentage points)
              [abandoned session; last committed snapshot unchanged]
  STAC B0: 1000/1000 (100 percentage points)
              [zarr updated, STAC JSON not — stale metadata persists]
  STAC B1: 1000/1000 pre-sweep → 0/1000 post-sweep
              [write-ordering does not prevent F1; sweeper detects and corrects
               the mismatch by recomputing sha256 from zarr and overwriting STAC]

F2 — crash after metadata update, before data write:
  Icechunk:   0/1000 (measured, not asserted: `icechunk_is_metadata_ahead_of_data`
              checks the committed snapshot directly for a metadata-ahead-of-data
              state after the only crash path Icechunk has — an abandoned session.
              There is no metadata-before-data write order to inject a fault into,
              since both are written in the same session and co-committed atomically;
              this measurement makes that structural property falsifiable rather than
              assumed — a future change that split the commit would flip it to True)
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

=== NIRD/Sigma2 S3-compatible object store (100 trials, Icechunk only) ===

F1 — crash after data write, before metadata update:
  Icechunk:   0/100 inconsistencies (0 percentage points)
              [identical mechanism to local FS: abandoned session, last committed
               snapshot unchanged — but here the "commit" is a conditional write
               (compare-and-swap) against the object store, not a POSIX rename]

F2 — crash after metadata update, before data write:
  Icechunk:   0/100 (measured via `icechunk_is_metadata_ahead_of_data`, identical
              method and reasoning to local FS — see above)

F3 — concurrent reader during in-progress write:
  Icechunk:   0/100 (readonly_session reads the last committed snapshot;
              in-progress writer changes are invisible until the conditional-write
              commit succeeds)

The F1/F2/F3 result is identical in kind and in count (zero) to the local-filesystem
result. Note what these three scenarios actually exercise on this backend: the
abandoned-session path (F1), the committed-snapshot state directly (F2), and a
single-writer commit (F3). None of these issues a conditional write that contests an
already-moved branch tip — that is what F4, below, tests, and it is the scenario that
determines whether this backend's CAS implementation is what the claim needs it to be.

=== F4 — concurrent racing writers (the conditional-write / CAS test) ===

Two sessions branch from the same committed snapshot, write OVERLAPPING data to the same
array region (forcing a real conflict — Icechunk can silently rebase non-overlapping
edits, which would not test rejection), and both attempt to commit. Expected (CAS
enforced): the first commit succeeds and moves the branch tip; the second session is now
based on a stale tip and `Session.commit()` must raise `icechunk.ConflictError` (the exact
exception name, confirmed against the installed icechunk==2.0.6 API — the `commit()`
docstring states: "If the session is out of date, this will raise a ConflictError
exception depicting the conflict that occurred").

  Local filesystem (1000 trials, seed=42):
    inconsistent:         0/1000  (store always ends in a single coherent state)
    conflict_rejected: 1000/1000  (icechunk.ConflictError raised on every stale commit)
  → POSIX rename also enforces a form of compare-and-swap at the filesystem level, so
    this result was expected; it confirms the F4 harness code itself works and measures
    what it claims to measure (an assertion-style check would fail loudly if
    `ConflictError` were not raised, or if the wrong exception name had been pinned —
    this was first verified with a 20-trial unit test before the full 1000-trial run).

  NIRD/Sigma2 S3-compatible object store (100 trials, seed=43, run with live `MINIO_*`
  credentials — the run that determines whether the conditional-write guarantee, the
  actual subject of the claim on object stores, holds on NIRD):
    inconsistent:       0/100  (store always ends in a single coherent state)
    conflict_rejected: 100/100  (icechunk.ConflictError raised on every stale commit,
                        over a real network round-trip against a production
                        S3-compatible endpoint, not a local POSIX filesystem)

  This is the positive control, green, on the real target backend: every stale-tip
  commit was rejected, and the store was never observed in a mixed/blended state. Had
  `conflict_rejected` been False on any NIRD trial — the object store accepting a commit
  from a stale tip — that would itself have been the headline finding (a Contradicted or
  qualified result), not a footnote. It was not observed; the conditional-write guarantee
  holds on NIRD/Sigma2, identically in kind to the local-filesystem result and confirmed
  independently over a real network against a production object store.
```

### Describe what limits the conclusions of the study (textarea, optional)

```
Object-store trial count is smaller than the local-FS sweep: 100 trials per scenario
(including F4, the scenario this Outcome's Validated status now rests on most heavily) on
NIRD/Sigma2 versus 1000 on local filesystem (see `harness/run_matrix.py` — each
object-store trial creates a remote repo over a real network round-trip, so the count is
deliberately reduced; the harness's own rationale is that 100 trials "is sufficient to
establish the pattern; expand if needed"). Zero inconsistencies (and zero unrejected
conflicts) in 100 trials is meaningfully different from zero in 1000 — a rare bug with
per-trial probability between roughly 1% and 0.1% could be present but unobserved at this
sample size. This is the main reason Confidence is HighConfidence rather than
VeryHighConfidence: the conclusion is unambiguous at the sample size tested, but the
sample is an order of magnitude smaller than the local-FS sweep. Expanding the
object-store run to 1000 trials (matching local FS) would close this residual gap and is
the natural follow-on, should stronger confidence be wanted later.

Single object-store provider tested: only NIRD/Sigma2 S3-compatible storage was
exercised. Different S3-compatible implementations (AWS S3 itself, other MinIO
deployments, other national e-infrastructure providers) may differ in their conditional-
write semantics or consistency guarantees; this result does not generalise automatically
to "all object stores," only to "the conditional-write path that NIRD's implementation
provides, which behaved correctly here."

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

F5–F6 (partial batch failure, other concurrency patterns) remain out of scope for this
vertical slice. F4 (concurrent competing writers) is now in scope, implemented, and run
to completion on both backends — see above.

Icechunk 2.0.6 warns that the local filesystem store is "not safe for concurrent
commits." Our scenarios involve a single writer at a time (F1/F2/F3), so this does not
affect the reported results on either backend — but it is a further reason the
object-store result, not the local-FS result, should be treated as the primary evidence
for the claim: local filesystem is explicitly documented by Icechunk as a
development/testing convenience, not the production target.

Test repos created on NIRD during this run (under
`jeani-ns1000k-grid4earth/icechunk-atomicity-test/<run_id>/`) are left in the bucket —
no automatic cleanup is performed by the harness (see `harness/run_matrix.py`).
```

---

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 05.
Use that URI in `06_citation.md` field "Identifier for the citing creative work".

> **Status:** Validated / HighConfidence / `confirms`. This reflects two corrections in
> sequence (see the 2026-06-07 history note at the top of this file): an early Validated
> upgrade was reverted because F1/F2/F3 alone don't test the conditional-write (CAS)
> mechanism the claim is specifically about; F4 (concurrent racing writers) was then
> implemented, unit-tested locally, and — critically — **run for real against NIRD/Sigma2
> with live `MINIO_*` credentials**, producing the positive control this Outcome's own
> prior correction said would be required: `conflict_rejected == True` and
> `inconsistent == False` in 100/100 trials on the actual object-store target, plus an
> identical 1000/1000 result on local filesystem as a sanity check. Every sub-claim —
> commit-or-abandon atomicity, snapshot isolation, metadata-ahead-of-data absence (now
> measured, not asserted, for Icechunk's F2), and conditional-write CAS — is now backed
> by measured evidence in its target environment. `06_citation.md` should use CiTO
> relation `confirms`.

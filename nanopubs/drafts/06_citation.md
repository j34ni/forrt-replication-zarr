# 06 — CiTO Citation

**Description:** *"Declare citations between papers or other works, using Citation Typing Ontology"*

> This is a question-rooted chain (no upstream paper). The CiTO cites the public
> document that articulates the claim we tested (`confirms`), plus the Icechunk
> specification that defines the protocol used as the intervention (`usesMethodIn`).

---

## Field-by-field draft

### Identifier for the citing creative work (text input, required)

URI of the Outcome published in step 05. Pull from `nanopubs/PUBLISHED.md`.

```
TBD — paste Outcome URI after publishing step 05
```

### List citations (repeatable group, required ≥1)

#### Citation 1 — Development Seed prototype (source of record for the claim)

##### Citation Type (dropdown)

```
confirms
```

> Rationale: Validation status is Validated / HighConfidence. The fault matrix has been
> run to completion on both backends — local filesystem (1000 trials × F1/F2/F3/F4) and
> a real object-store backend, NIRD/Sigma2 S3-compatible storage (100 trials ×
> F1/F2/F3/F4) — covering every sub-claim in the headline claim:
>   - F1/F2/F3: 0 inconsistencies on both backends — commit-or-abandon atomicity,
>     snapshot isolation, and (for F2, now measured rather than asserted) absence of a
>     metadata-ahead-of-data state.
>   - F4 (concurrent racing writers — the scenario that actually contests the branch tip
>     and tests conditional-write/CAS, the mechanism the claim attributes specifically to
>     object stores): `conflict_rejected == True` and `inconsistent == False` in
>     **100/100 NIRD/Sigma2 trials** (and 1000/1000 on local filesystem as a sanity
>     check) — run for real with live `MINIO_*` credentials, not asserted from code or
>     inferred from a unit test alone.
> The positive control for the conditional-write guarantee came back green on the actual
> target backend. Every part of the claim — including the part that is *specific* to
> object stores and the reason this replication targeted NIRD in the first place — is now
> backed by measured evidence in its target environment. CiTO intention = `confirms`. See
> `05_outcome.md` for the full Validated / HighConfidence rationale and both backends'
> F1-F4 results.
>
> (Two corrections preceded this conclusion, both kept in `05_outcome.md`'s history note
> for the audit trail: an early premature `confirms`/Validated upgrade based on F1-F3
> alone was reverted to `qualifies`/PartiallySupported; F4 was then implemented,
> unit-tested, and — the step that actually closes the gap — run for real against NIRD,
> producing the evidence that justifies this final `confirms`.)

##### DOI or other URL of the cited work (text input)

```
https://github.com/developmentseed/zarr-datafusion-search
```

---

#### Citation 2 — Icechunk specification (protocol reference)

##### Citation Type (dropdown)

```
usesMethodIn
```

> Rationale: the intervention (Icechunk atomic commit) is defined in the Icechunk
> specification. The harness uses the session → commit → readonly_session protocol
> described there.

##### DOI or other URL of the cited work (text input)

```
https://icechunk.io/en/latest/reference/spec/
```

---

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 06.

This completes the six-step FORRT chain:
PICO → AIDA → Claim → Study → Outcome → CiTO ✓

**Optional next layers:**
- **Research Software** (`07_research_software.md`) — the fault-injection harness
  is a reusable artefact; its RS nanopub one-way cites the FORRT Claim URI.
- **Research Synthesis** (`08_synthesis.md`) — if this chain is later combined with
  an F5–F6 extension (partial batch failure, other concurrency patterns) or with
  results from additional object-store providers beyond NIRD/Sigma2, into a
  cross-cutting synthesis.

**Status check before publishing:** F4 has been run to completion on both backends with
live `MINIO_*` credentials (100/100 NIRD trials, 1000/1000 local trials —
`conflict_rejected == True`, `inconsistent == False` throughout); `05_outcome.md` has
been updated with the measured counts and the status moved to Validated / HighConfidence.
This CiTO relation (`confirms`) and the Outcome status it depends on now reflect a
complete picture, grounded in measured results from the actual target environment.

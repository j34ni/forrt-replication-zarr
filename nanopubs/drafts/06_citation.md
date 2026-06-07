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

> Rationale: Validation status is now Validated — the fault matrix was run on both
> the local filesystem backend (1000 trials × F1/F2/F3, 0 inconsistencies) and a real
> object-store backend, NIRD/Sigma2 S3-compatible storage (100 trials × F1/F2/F3,
> 0 inconsistencies), reproducing the same zero-inconsistency result in the claim's
> actual target environment (object stores with conditional writes), not merely on
> local filesystem as a proxy for it. CiTO intention = `confirms`. See `05_outcome.md`
> for the full Validated / HighConfidence rationale and both backends' results.

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
  the F4–F6 extension (concurrent competing writers, partial batch failure) or with
  results from additional object-store providers beyond NIRD/Sigma2, into a
  cross-cutting synthesis.

"""
Fault scenario runners: F1, F2, F3 for each system.

Each function runs one trial and returns whether an inconsistency was observed.
The caller (run_matrix.py) calls these N times per scenario × system × backend.

Scenarios:
  F1 — crash after data write, before metadata update.
  F2 — crash after metadata update, before data write (STAC only; Icechunk not applicable).
  F3 — concurrent reader observes store mid-write.

written, untested
"""
import tempfile
from pathlib import Path

import numpy as np

from harness.invariant import (
    check_icechunk,
    check_stac,
    compute_sha256,
    icechunk_is_metadata_ahead_of_data,
)
from harness.baseline_stac import (
    stac_initial_write,
    stac_b0_update,
    stac_b0_update_reverse_order,
    stac_b0_mid_write_check,
    stac_b1_update,
    stac_b1_sweeper,
    stac_b1_mid_write_check,
    SimulatedCrash,
)
from harness.baseline_icechunk import (
    icechunk_initial_write,
    icechunk_update_abandoned,
    icechunk_read_during_write,
    icechunk_racing_writers,
)


def _random_data(rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(256).astype("float32")


# ---------------------------------------------------------------------------
# F1 — crash after data, before metadata
# ---------------------------------------------------------------------------

def f1_icechunk(repo, rng: np.random.Generator) -> bool:
    """Icechunk F1: abandon session before commit. Expect: no inconsistency."""
    data_v1 = _random_data(rng)
    icechunk_initial_write(repo, data_v1)

    data_v2 = _random_data(rng)
    icechunk_update_abandoned(repo, data_v2)

    consistent, _, _ = check_icechunk(repo)
    return not consistent  # True = inconsistency observed (expected: False)


def f1_stac_b0(zarr_path: str, stac_path: str, rng: np.random.Generator) -> bool:
    """STAC B0 F1: write zarr, crash before STAC update. Expect: inconsistency."""
    data_v1 = _random_data(rng)
    stac_initial_write(zarr_path, stac_path, data_v1)

    data_v2 = _random_data(rng)
    try:
        stac_b0_update(zarr_path, stac_path, data_v2, fault_point="after_data")
    except SimulatedCrash:
        pass

    consistent, _, _ = check_stac(zarr_path, stac_path)
    return not consistent  # True = inconsistency observed (expected: True)


def f1_stac_b1(zarr_path: str, stac_path: str, rng: np.random.Generator) -> tuple[bool, bool]:
    """
    STAC B1 F1: write zarr, crash before STAC update, then run sweeper.
    Returns (pre_sweep_inconsistent, post_sweep_inconsistent).
    Expected: (True, False) — inconsistency exists until sweeper runs.
    """
    data_v1 = _random_data(rng)
    stac_initial_write(zarr_path, stac_path, data_v1)

    data_v2 = _random_data(rng)
    try:
        stac_b1_update(zarr_path, stac_path, data_v2, fault_point="after_data")
    except SimulatedCrash:
        pass

    consistent_pre, _, _ = check_stac(zarr_path, stac_path)
    stac_b1_sweeper(zarr_path, stac_path)
    consistent_post, _, _ = check_stac(zarr_path, stac_path)
    return not consistent_pre, not consistent_post


# ---------------------------------------------------------------------------
# F2 — crash after metadata update, before data write
# ---------------------------------------------------------------------------

def f2_icechunk(repo, rng: np.random.Generator) -> bool:
    """
    F2-state measurement for Icechunk: runs the only crash path Icechunk has
    (abandon a session before commit — there is no metadata-before-data write
    order to inject a fault into, since both are written in the same session and
    co-committed atomically), then checks whether the *committed* snapshot is
    ever in an F2 state (attrs reference a sha256 the committed array doesn't hold).

    This mirrors `f2_stac_b1`: rather than asserting "not applicable", it measures
    the F2 *state* directly via `icechunk_is_metadata_ahead_of_data`, so a future
    change to the write path that split metadata and data into separate commits
    would be caught by this test flipping to True.

    Returns True if metadata is ahead of data (F2 state observed) — expected: False.
    """
    data_v1 = _random_data(rng)
    icechunk_initial_write(repo, data_v1)

    data_v2 = _random_data(rng)
    new_sha256 = compute_sha256(data_v2)
    icechunk_update_abandoned(repo, data_v2)

    return icechunk_is_metadata_ahead_of_data(repo, new_sha256)


def f2_stac_b0(zarr_path: str, stac_path: str, rng: np.random.Generator) -> bool:
    """STAC B0 F2: write STAC, crash before zarr write. Expect: inconsistency."""
    data_v1 = _random_data(rng)
    stac_initial_write(zarr_path, stac_path, data_v1)

    data_v2 = _random_data(rng)
    try:
        stac_b0_update_reverse_order(zarr_path, stac_path, data_v2, fault_point="after_data")
    except SimulatedCrash:
        pass

    consistent, _, _ = check_stac(zarr_path, stac_path)
    return not consistent  # True = inconsistency observed (expected: True)


def f2_stac_b1(zarr_path: str, stac_path: str, rng: np.random.Generator) -> bool:
    """
    F2-state measurement for B1: runs B1's real write path with a crash, then checks
    whether the store is ever in an F2 state (STAC ahead of data — STAC references a
    sha256 that the zarr array doesn't contain).

    B1 enforces data-before-STAC ordering, so the F2 fault injection (crash between
    a metadata write and a data write) cannot be replicated in B1 — there is no
    metadata-before-data path to inject a fault into. Instead we measure the F2 *state*
    directly after B1's real crash scenario, which is always an F1-type crash (data
    written, STAC not yet updated). STAC should never be ahead of the data.

    Returns True if STAC is ahead of data (F2 state observed) — expected: False.
    Measuring this rather than asserting it makes the result falsifiable: a future
    write-order regression in B1 would flip this to True.
    """
    from harness.invariant import stac_is_ahead_of_data
    data_v1 = _random_data(rng)
    stac_initial_write(zarr_path, stac_path, data_v1)

    data_v2 = _random_data(rng)
    new_sha256 = compute_sha256(data_v2)

    try:
        stac_b1_update(zarr_path, stac_path, data_v2, fault_point="after_data")
    except SimulatedCrash:
        pass

    return stac_is_ahead_of_data(zarr_path, stac_path, new_sha256)


# ---------------------------------------------------------------------------
# F3 — concurrent reader during write
# ---------------------------------------------------------------------------

def f3_icechunk(repo, rng: np.random.Generator) -> bool:
    """
    Icechunk F3: reader uses a fresh readonly_session during an in-progress write.
    The readonly_session reads the last committed snapshot — never mid-write state.
    Expect: no inconsistency observed mid-write.
    """
    data_v1 = _random_data(rng)
    icechunk_initial_write(repo, data_v1)

    data_v2 = _random_data(rng)
    mid_consistent, post_consistent = icechunk_read_during_write(repo, data_v2)

    # inconsistency = mid-write reader saw a mixed state
    return not mid_consistent  # expected: False


def f3_stac_b0(zarr_path: str, stac_path: str, rng: np.random.Generator) -> bool:
    """STAC B0 F3: reader sees zarr with new data but STAC with old sha256. Expect: inconsistency."""
    data_v1 = _random_data(rng)
    stac_initial_write(zarr_path, stac_path, data_v1)

    data_v2 = _random_data(rng)
    inconsistency_observed = stac_b0_mid_write_check(zarr_path, stac_path, data_v2)
    return inconsistency_observed  # expected: True


def f3_stac_b1(zarr_path: str, stac_path: str, rng: np.random.Generator) -> bool:
    """
    STAC B1 F3: same inconsistency window as B0 — write-ordering doesn't close F3.
    The sweeper helps for F1 but runs asynchronously; it does not protect the F3 window.
    """
    data_v1 = _random_data(rng)
    stac_initial_write(zarr_path, stac_path, data_v1)

    data_v2 = _random_data(rng)
    inconsistency_observed = stac_b1_mid_write_check(zarr_path, stac_path, data_v2)
    return inconsistency_observed  # expected: True


# ---------------------------------------------------------------------------
# F4 — concurrent writers racing for the same branch tip (Icechunk only)
#
# F1-F3 all pass on any storage backend because they only exercise Icechunk's
# session commit-or-abandon model and snapshot isolation — properties of the
# session API that hold independent of whether the underlying store supports
# conditional writes (compare-and-swap on the branch tip). F4 is the scenario
# that actually depends on CAS: two writers branch from the same committed tip,
# edit the SAME region, and race to commit. The store must reject the loser's
# stale-tip commit. This is the only scenario whose outcome on an object store
# can differ from its outcome on a local filesystem for a structural reason
# (POSIX rename vs. S3 conditional PUT/If-Match), which is what makes it the
# right test to run against NIRD/Sigma2 to validate the conditional-write claim.
# ---------------------------------------------------------------------------

def f4_icechunk_racing_writers(repo, rng: np.random.Generator) -> dict:
    """
    F4: two sessions branch from the same committed snapshot and write to the
    SAME array region, then both attempt to commit.

    Returns a dict with two independently meaningful fields (see
    `icechunk_racing_writers` for the full rationale):
      - "inconsistent": the store ends in a mixed/blended state (expected: False —
        the consistency invariant must hold regardless of which writer wins)
      - "conflict_rejected": the second commit raised icechunk.ConflictError —
        the positive control for the conditional-write guarantee (expected: True;
        if this is ever False on an object store, *that* is the finding — it means
        CAS did not protect the branch tip there)
    """
    data_v0 = _random_data(rng)
    icechunk_initial_write(repo, data_v0)

    data_a = _random_data(rng)
    data_b = _random_data(rng)
    consistent, conflict_rejected = icechunk_racing_writers(repo, data_a, data_b)

    return {"inconsistent": not consistent, "conflict_rejected": conflict_rejected}

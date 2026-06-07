"""
Icechunk baseline operations.

All data + metadata writes happen inside a single session. The session is either
committed (atomic, fully visible) or abandoned (nothing visible). There is no partial
state reachable by a reader using a separate readonly_session.

written, untested
"""
import numpy as np
import zarr
import icechunk

from harness.invariant import check_icechunk, compute_sha256


def icechunk_initial_write(repo: icechunk.Repository, data: np.ndarray) -> str:
    """Write initial data + sha256 attr to a fresh repo. Returns snapshot id."""
    session = repo.writable_session("main")
    store = session.store
    root = zarr.open_group(store=store, mode="w")
    arr = root.create_array("data", shape=data.shape, dtype=data.dtype)
    arr[:] = data
    root.attrs.update({"data_sha256": compute_sha256(data)})
    return session.commit("initial write")


def icechunk_update_committed(repo: icechunk.Repository, new_data: np.ndarray) -> str:
    """Normal update: write new data + updated sha256 attr, commit. Returns snapshot id."""
    session = repo.writable_session("main")
    store = session.store
    root = zarr.open_group(store=store, mode="a")
    root["data"][:] = new_data
    root.attrs.update({"data_sha256": compute_sha256(new_data)})
    return session.commit("update data")


def icechunk_update_abandoned(repo: icechunk.Repository, new_data: np.ndarray) -> None:
    """
    Simulate a crash: open session, write data + attr, then abandon without committing.
    The session object goes out of scope; no commit is issued.
    This is the Icechunk equivalent of a process crash mid-write.
    """
    session = repo.writable_session("main")
    store = session.store
    root = zarr.open_group(store=store, mode="a")
    root["data"][:] = new_data
    root.attrs.update({"data_sha256": compute_sha256(new_data)})
    # deliberately NOT calling session.commit() — session is abandoned here


def icechunk_read_during_write(
    repo: icechunk.Repository,
    new_data: np.ndarray,
) -> tuple[bool, bool]:
    """
    Simulate F3: open a writable session, write (without committing), then check
    what a concurrent readonly_session sees. Returns (mid_write_consistent, post_commit_consistent).
    """
    session = repo.writable_session("main")
    store = session.store
    root = zarr.open_group(store=store, mode="a")
    root["data"][:] = new_data
    root.attrs.update({"data_sha256": compute_sha256(new_data)})

    # A concurrent reader opens a fresh readonly session — reads last committed snapshot.
    from harness.invariant import check_icechunk
    mid_write_consistent, _, _ = check_icechunk(repo)

    session.commit("update data")

    post_commit_consistent, _, _ = check_icechunk(repo)
    return mid_write_consistent, post_commit_consistent


def icechunk_racing_writers(
    repo: icechunk.Repository,
    data_a: np.ndarray,
    data_b: np.ndarray,
) -> tuple[bool, bool]:
    """
    F4: two writable sessions branch from the same committed tip and write to the
    SAME array region — a real overlap, forced deliberately. Icechunk's rebase
    machinery can silently merge non-overlapping chunk edits (both succeed, which
    is also consistent but does not exercise rejection); only an overlapping edit
    forces the compare-and-swap-on-branch-tip path this scenario is meant to test.

    The first commit succeeds and moves the branch tip. The second session is now
    based on a stale tip; Session.commit() must reject it. Confirmed against the
    installed icechunk==2.0.6 API (`Session.commit` docstring): "If the session is
    out of date, this will raise a ConflictError exception depicting the conflict
    that occurred." — so we catch `icechunk.ConflictError` specifically, not a
    generic exception.

    Returns (consistent, conflict_rejected):
      - consistent: the store ends in a single coherent state (stored sha256
        matches recomputed data) — expected True regardless of which writer wins.
      - conflict_rejected: the second commit raised ConflictError — the positive
        control for the conditional-write guarantee. If this is ever False, the
        object store accepted a write from a stale tip and CAS does not hold there;
        that is the finding F1-F3 cannot surface (they never contest the tip).
    """
    sess_a = repo.writable_session("main")
    sess_b = repo.writable_session("main")  # branches from the same tip as sess_a

    for sess, data in ((sess_a, data_a), (sess_b, data_b)):
        root = zarr.open_group(store=sess.store, mode="a")
        root["data"][:] = data
        root.attrs.update({"data_sha256": compute_sha256(data)})

    sess_a.commit("writer A")

    conflict_rejected = False
    try:
        sess_b.commit("writer B")
    except icechunk.ConflictError:
        conflict_rejected = True

    consistent, _, _ = check_icechunk(repo)
    return consistent, conflict_rejected

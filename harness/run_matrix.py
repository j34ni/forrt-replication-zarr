"""
Matrix runner: scenarios × systems × backends × N trials → results.parquet

Usage:
    # local only (default):
    python -m harness.run_matrix --trials 1000 --out data/results/results.parquet

    # include MinIO backend (set env vars first):
    export MINIO_ENDPOINT=https://s3.nird.sigma2.no
    export MINIO_BUCKET=jeani-ns1000k-grid4earth
    export MINIO_PREFIX=icechunk-atomicity-test
    export MINIO_ACCESS_KEY=<key>
    export MINIO_SECRET_KEY=<secret>
    python -m harness.run_matrix --trials 1000 --minio-trials 100 --out data/results/results.parquet

MinIO uses fewer trials by default (--minio-trials 100) because each trial creates
a remote repo — 100 trials is sufficient to establish the pattern; expand if needed.

All test repos are written under MINIO_PREFIX/<run-id>/ and left in the bucket
after the run (no automatic cleanup). Clean up via the MinIO console under
that prefix when done.
"""
import argparse
import datetime
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from harness.backends import (
    local_icechunk_repo,
    minio_icechunk_repo,
    minio_env_set,
    probe_minio,
)
from harness.faults import (
    f1_icechunk, f1_stac_b0, f1_stac_b1,
    f2_icechunk, f2_stac_b0, f2_stac_b1,
    f3_icechunk, f3_stac_b0, f3_stac_b1,
    f4_icechunk_racing_writers,
)


# ---------------------------------------------------------------------------
# Local backend
# ---------------------------------------------------------------------------

def run_local_trials(n_trials: int, seed: int = 42) -> list[dict]:
    """Run F1/F2/F3 for all three systems on the local filesystem backend."""
    rng = np.random.default_rng(seed)
    rows: list[dict] = []

    for trial in range(n_trials):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # F1 — crash after data, before metadata
            ic_repo = local_icechunk_repo(str(base / "ic_f1"))
            rows.append({
                "scenario": "F1", "backend": "local", "system": "icechunk",
                "trial": trial,
                "inconsistent": f1_icechunk(ic_repo, rng),
                "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
                "notes": "",
            })
            rows.append({
                "scenario": "F1", "backend": "local", "system": "stac_b0",
                "trial": trial,
                "inconsistent": f1_stac_b0(str(base / "zarr_f1"), str(base / "stac_f1.json"), rng),
                "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
                "notes": "",
            })
            pre, post = f1_stac_b1(str(base / "zarr_f1b"), str(base / "stac_f1b.json"), rng)
            rows.append({
                "scenario": "F1", "backend": "local", "system": "stac_b1",
                "trial": trial,
                "inconsistent": pre,
                "pre_sweep_inconsistent": pre, "post_sweep_inconsistent": post,
                "notes": "pre/post sweeper recorded separately",
            })

            # F2 — crash after metadata, before data
            rows.append({
                "scenario": "F2", "backend": "local", "system": "icechunk",
                "trial": trial,
                "inconsistent": f2_icechunk(local_icechunk_repo(str(base / "ic_f2")), rng),
                "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
                "notes": "F2-state measured: is committed metadata ever ahead of committed data after an abandoned session? (expected False — Icechunk co-commits both; no metadata-before-data path exists to crash inside)",
            })
            rows.append({
                "scenario": "F2", "backend": "local", "system": "stac_b0",
                "trial": trial,
                "inconsistent": f2_stac_b0(str(base / "zarr_f2"), str(base / "stac_f2.json"), rng),
                "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
                "notes": "",
            })
            rows.append({
                "scenario": "F2", "backend": "local", "system": "stac_b1",
                "trial": trial,
                "inconsistent": f2_stac_b1(str(base / "zarr_f2b"), str(base / "stac_f2b.json"), rng),
                "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
                "notes": "F2-state measured: is STAC ever ahead of data after B1 crash? (expected False)",
            })

            # F3 — concurrent reader during write
            ic_repo_f3 = local_icechunk_repo(str(base / "ic_f3"))
            rows.append({
                "scenario": "F3", "backend": "local", "system": "icechunk",
                "trial": trial,
                "inconsistent": f3_icechunk(ic_repo_f3, rng),
                "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
                "notes": "",
            })
            rows.append({
                "scenario": "F3", "backend": "local", "system": "stac_b0",
                "trial": trial,
                "inconsistent": f3_stac_b0(str(base / "zarr_f3"), str(base / "stac_f3.json"), rng),
                "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
                "notes": "",
            })
            rows.append({
                "scenario": "F3", "backend": "local", "system": "stac_b1",
                "trial": trial,
                "inconsistent": f3_stac_b1(str(base / "zarr_f3b"), str(base / "stac_f3b.json"), rng),
                "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
                "notes": "write-ordering does not close F3 window; sweeper not invoked (retroactive fix cannot prevent a read that already occurred)",
            })

            # F4 — concurrent racing writers (Icechunk only; the actual CAS test —
            # see harness/faults.py for why F1-F3 don't exercise conditional writes)
            ic_repo_f4 = local_icechunk_repo(str(base / "ic_f4"))
            f4_result = f4_icechunk_racing_writers(ic_repo_f4, rng)
            rows.append({
                "scenario": "F4", "backend": "local", "system": "icechunk",
                "trial": trial,
                "inconsistent": f4_result["inconsistent"],
                "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
                "conflict_rejected": f4_result["conflict_rejected"],
                "notes": "positive control for conditional-write/CAS guarantee: conflict_rejected expected True (stale-tip commit raises icechunk.ConflictError); inconsistent expected False regardless of which writer wins",
            })

    return rows


# ---------------------------------------------------------------------------
# MinIO backend — Icechunk only
# ---------------------------------------------------------------------------
# STAC baseline results are backend-agnostic (inconsistency is a structural property
# of the two-step write, not of the storage layer). Only the Icechunk side is tested
# on MinIO: the key question is whether conditional writes on this object store
# preserve the atomicity guarantee.

def run_minio_icechunk_trials(n_trials: int, run_id: str, seed: int = 42) -> list[dict]:
    """
    Run F1/F2/F3 for Icechunk on the MinIO backend.

    Each trial gets its own repo prefix: <MINIO_PREFIX>/<run_id>/trial-<N>/<scenario>/
    Repos are left in the bucket after the run — clean up via the MinIO console.
    """
    rng = np.random.default_rng(seed + 1)  # different seed from local run
    rows: list[dict] = []

    for trial in range(n_trials):
        trial_prefix = f"{run_id}/trial-{trial:04d}"

        # F1
        repo_f1 = minio_icechunk_repo(f"{trial_prefix}/f1")
        rows.append({
            "scenario": "F1", "backend": "minio", "system": "icechunk",
            "trial": trial,
            "inconsistent": f1_icechunk(repo_f1, rng),
            "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
            "notes": "",
        })

        # F2 — measured, not asserted (same reasoning as local)
        repo_f2 = minio_icechunk_repo(f"{trial_prefix}/f2")
        rows.append({
            "scenario": "F2", "backend": "minio", "system": "icechunk",
            "trial": trial,
            "inconsistent": f2_icechunk(repo_f2, rng),
            "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
            "notes": "F2-state measured: is committed metadata ever ahead of committed data after an abandoned session? (expected False — Icechunk co-commits both; no metadata-before-data path exists to crash inside)",
        })

        # F3
        repo_f3 = minio_icechunk_repo(f"{trial_prefix}/f3")
        rows.append({
            "scenario": "F3", "backend": "minio", "system": "icechunk",
            "trial": trial,
            "inconsistent": f3_icechunk(repo_f3, rng),
            "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
            "notes": "",
        })

        # F4 — concurrent racing writers: the actual conditional-write/CAS test.
        # This is THE scenario that justifies running on a real object store —
        # see harness/faults.py for why F1-F3 pass on any backend regardless of CAS.
        repo_f4 = minio_icechunk_repo(f"{trial_prefix}/f4")
        f4_result = f4_icechunk_racing_writers(repo_f4, rng)
        rows.append({
            "scenario": "F4", "backend": "minio", "system": "icechunk",
            "trial": trial,
            "inconsistent": f4_result["inconsistent"],
            "pre_sweep_inconsistent": None, "post_sweep_inconsistent": None,
            "conflict_rejected": f4_result["conflict_rejected"],
            "notes": "positive control for conditional-write/CAS guarantee on a real object store: conflict_rejected expected True; if False here, that is itself the headline finding (CAS did not protect the branch tip on NIRD/Sigma2)",
        })

        if (trial + 1) % 10 == 0:
            print(f"  MinIO: {trial + 1}/{n_trials} trials done")

    return rows


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_all(
    n_trials: int = 1000,
    minio_trials: int = 100,
    out_path: str = "data/results/results.parquet",
    seed: int = 42,
) -> pd.DataFrame:
    print(f"Running local backend ({n_trials} trials)...")
    rows = run_local_trials(n_trials=n_trials, seed=seed)
    print(f"  local: {len(rows)} rows")

    if minio_env_set():
        reachable, msg = probe_minio()
        if reachable:
            run_id = datetime.datetime.now(datetime.UTC).strftime("run-%Y%m%dT%H%M%S")
            print(f"Running MinIO backend ({minio_trials} trials, run_id={run_id})...")
            minio_rows = run_minio_icechunk_trials(
                n_trials=minio_trials, run_id=run_id, seed=seed
            )
            rows.extend(minio_rows)
            print(f"  minio: {len(minio_rows)} rows")
        else:
            print(f"MinIO env vars set but endpoint unreachable ({msg}) — skipping.")
    else:
        print("MinIO env vars not set — skipping minio backend.")

    df = pd.DataFrame(rows)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"Results written to {out_path} ({len(df)} rows)")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=1000,
                        help="local backend trial count")
    parser.add_argument("--minio-trials", type=int, default=100,
                        help="MinIO backend trial count (Icechunk only)")
    parser.add_argument("--out", default="data/results/results.parquet")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run_all(
        n_trials=args.trials,
        minio_trials=args.minio_trials,
        out_path=args.out,
        seed=args.seed,
    )

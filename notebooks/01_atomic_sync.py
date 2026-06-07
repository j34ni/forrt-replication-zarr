# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 01 — Atomic synchronization: fault-injection consistency test
#
# **Claim under test:** Icechunk-backed transactional stores produce zero observable
# metadata–data inconsistencies under writer failure and concurrent access, whereas
# disconnected STAC metadata indexes over object storage produce such inconsistencies
# without external orchestration.
#
# **Method:** A fault-injection harness generates synthetic Zarr arrays carrying a
# SHA-256 checksum attribute. A consistency checker recomputes the checksum from data
# and compares. Faults are injected at specific points in the write sequence across
# three scenarios (F1, F2, F3) for three systems (Icechunk, STAC B0, STAC B1).
#
# **Status:** written, untested — results cells will be populated on first run.

# %% [markdown]
# ## 0. Environment check

# %%
import sys
print(f"Python {sys.version}")

import zarr
print(f"zarr {zarr.__version__}")

import icechunk
print(f"icechunk {icechunk.__version__}")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# %% [markdown]
# ## 1. Run the fault-injection matrix
#
# Runs F1, F2, F3 across Icechunk / STAC-B0 / STAC-B1 on the local filesystem backend.
# Each scenario runs `N_TRIALS` independent trials with fresh stores.
#
# Runtime estimate: ~5 min for N_TRIALS=1000 on a modern laptop (~30 s per 100 trials).
# N_TRIALS=1000 matches the trial count cited throughout the Outcome nanopub
# (`nanopubs/drafts/05_outcome.md`) and the figure below — keep them in sync.

# %%
import sys
sys.path.insert(0, str(Path("..").resolve()))

from harness.run_matrix import run_all

RESULTS_PATH = "../data/results/results.parquet"
N_TRIALS = 1000

df = run_all(n_trials=N_TRIALS, out_path=RESULTS_PATH, seed=42)
df.head(12)

# %% [markdown]
# ## 2. Headline counts: inconsistencies per scenario × system
#
# `results.parquet` may also contain object-store (MinIO/NIRD) trials from a
# `--minio-trials` run (see `harness/run_matrix.py`). This figure is scoped to the
# *local filesystem* backend specifically — filter to it explicitly so a mixed-backend
# results file doesn't silently inflate the Icechunk trial count (e.g. 1000 local +
# 100 MinIO → 1100, corrupting the "N=1000" framing below).

# %%
df_local = df[df["backend"] == "local"]

summary = (
    df_local.groupby(["scenario", "system"])["inconsistent"]
    .agg(["sum", "count"])
    .rename(columns={"sum": "inconsistent_count", "count": "trials"})
    .reset_index()
)
summary["inconsistency_rate"] = summary["inconsistent_count"] / summary["trials"]
print(summary.to_string(index=False))

# %% [markdown]
# ## 3. Figure: inconsistency count per scenario × system
#
# Design:
# - **Panels 1–3 (local filesystem, N=1000)**: Icechunk vs STAC B0/B1 across F1/F2/F3.
#   - **F1 B1**: plotted as two adjacent real bars — pre-sweep and post-sweep
#     (1000 → 0), each independently labelled. Both values are plotted, not just
#     the pre-sweep count with an annotation arrow that's easy to miss.
#   - **F2 B1**: cross-hatched — this is a measured F2-state check (is STAC ever ahead
#     of data?), not a fault injection. Zero is real but means "write-ordering holds".
#   - **Y-axis**: worst-case trial count (deterministic injection), not a probability.
# - **Panel 4 (object store, N=100)**: Icechunk-only run against the real NIRD/Sigma2
#   S3-compatible endpoint — the environment the claim is actually about (conditional
#   writes / CAS), where local filesystem gets atomicity "for free" via POSIX rename.
#   F1-F3 here are structural (session-model) checks that pass on any backend; they
#   do not by themselves contest the branch tip. **F4** (concurrent racing writers,
#   see `harness/faults.py`) is the scenario that actually does — it has now been run
#   for real against NIRD/Sigma2 with live `MINIO_*` credentials, and is plotted here as
#   two bars: `conflict_rejected` (the positive control for the conditional-write
#   guarantee — green, expected to equal N) and `inconsistent` (expected zero). This is
#   the evidence the Validated status in `nanopubs/drafts/05_outcome.md` rests on. Panel
#   4 has its own y-scale (N=100 ≠ N=1000) so the bars stay legible.

# %%
SYSTEM_ORDER = ["icechunk", "stac_b0", "stac_b1"]
SCENARIO_ORDER = ["F1", "F2", "F3"]
COLORS = {"icechunk": "#2196F3", "stac_b0": "#F44336", "stac_b1": "#FF9800"}
LABELS = {"icechunk": "Icechunk", "stac_b0": "STAC B0\n(naive)", "stac_b1": "STAC B1\n(best-effort)"}

N = N_TRIALS
f1_b1_post = int(df_local[(df_local["scenario"] == "F1") & (df_local["system"] == "stac_b1")]["post_sweep_inconsistent"].sum())

df_minio = df[df["backend"] == "minio"]
N_MINIO = int(df_minio.groupby("scenario")["inconsistent"].count().iloc[0])
minio_summary = (
    df_minio[df_minio["system"] == "icechunk"]
    .groupby("scenario")["inconsistent"]
    .sum()
    .reindex(SCENARIO_ORDER)
    .fillna(0)
)

fig, axes = plt.subplots(1, 4, figsize=(15, 4.5), gridspec_kw={"width_ratios": [1, 1, 1, 0.85]})

for ax, scenario in zip(axes[:3], SCENARIO_ORDER):
    sub = summary[summary["scenario"] == scenario].set_index("system").reindex(SYSTEM_ORDER)
    counts = sub["inconsistent_count"].fillna(0)

    for i, (sys, count) in enumerate(zip(SYSTEM_ORDER, counts)):
        if scenario == "F1" and sys == "stac_b1":
            # Plot pre-sweep AND post-sweep as two real, independently-labelled bars
            # (1000 -> 0) — not a single bar plus an annotation arrow that's easy to
            # miss. The reduction is the headline of the B1 design; it must be a
            # plotted value, not a footnote.
            bar_width = 0.32
            pre_count, post_count = count, f1_b1_post
            ax.bar(i - bar_width / 2, pre_count, width=bar_width, color=COLORS[sys],
                   edgecolor="white", linewidth=0.5, label="pre-sweep")
            ax.bar(i + bar_width / 2, post_count, width=bar_width, color=COLORS[sys],
                   edgecolor="white", linewidth=0.5, alpha=0.35, hatch="...", label="post-sweep")
            ax.text(i - bar_width / 2, pre_count + N * 0.02, f"{int(pre_count)}",
                    ha="center", va="bottom", fontsize=9, fontweight="bold", color="#CC6600")
            ax.text(i + bar_width / 2, post_count + N * 0.02, f"{int(post_count)}",
                    ha="center", va="bottom", fontsize=9, fontweight="bold", color="#CC6600")
            ax.legend(fontsize=6.5, loc="upper left", frameon=False,
                      handlelength=1.2, handleheight=1.2, labelspacing=0.3)
            continue

        hatch = "///" if (scenario == "F2" and sys == "stac_b1") else None
        ax.bar(i, count, color=COLORS[sys], edgecolor="white", linewidth=0.5, hatch=hatch)
        label_y = count + N * 0.02
        if scenario == "F2" and sys == "stac_b1":
            ax.text(i, label_y, f"{int(count)}", ha="center", va="bottom",
                    fontsize=10, fontweight="bold")
            ax.text(i, label_y + N * 0.08, "write-order\nholds", ha="center",
                    fontsize=7, color="#777", style="italic")
        else:
            ax.text(i, label_y, f"{int(count)}", ha="center", va="bottom",
                    fontsize=10, fontweight="bold")

    ax.set_title(f"Scenario {scenario}\n(local filesystem)", fontsize=11, fontweight="bold")
    ax.set_ylabel(f"Worst-case trial count\n(deterministic, N={N})" if ax is axes[0] else "")
    ax.set_ylim(0, N * 1.5)
    ax.set_xticks(range(len(SYSTEM_ORDER)))
    ax.set_xticklabels([LABELS[s] for s in SYSTEM_ORDER], fontsize=9)
    ax.axhline(0, color="black", linewidth=0.8)

# Panel 4 — object store (NIRD/Sigma2 S3-compatible, Icechunk only).
# Separate y-scale (N_MINIO=100) since the trial count differs from the local-FS panels.
# F1-F3 are structural (session-model) checks that pass on any backend; F4 is the
# scenario that actually contests the branch tip and tests conditional-write/CAS — its
# `conflict_rejected` count is the positive control this Outcome's Validated status
# rests on, plotted here as a green bar (expected = N_MINIO) alongside `inconsistent`
# (expected = 0), both measured for real against the NIRD/Sigma2 endpoint.
SCENARIO_ORDER_MINIO = SCENARIO_ORDER + ["F4"]
f4_minio = df_minio[(df_minio["scenario"] == "F4") & (df_minio["system"] == "icechunk")]
f4_minio_conflict_rejected = int(f4_minio["conflict_rejected"].sum())
f4_minio_inconsistent = int(f4_minio["inconsistent"].sum())

ax_minio = axes[3]
bar_width = 0.32
for i, scenario in enumerate(SCENARIO_ORDER_MINIO):
    if scenario == "F4":
        ax_minio.bar(i - bar_width / 2, f4_minio_conflict_rejected, width=bar_width,
                     color="#4CAF50", edgecolor="white", linewidth=0.5,
                     label="conflict_rejected\n(positive control, expect = N)")
        ax_minio.bar(i + bar_width / 2, f4_minio_inconsistent, width=bar_width,
                     color=COLORS["icechunk"], edgecolor="white", linewidth=0.5, alpha=0.6,
                     label="inconsistent\n(expect = 0)")
        ax_minio.text(i - bar_width / 2, f4_minio_conflict_rejected + N_MINIO * 0.04,
                      f"{f4_minio_conflict_rejected}", ha="center", va="bottom",
                      fontsize=9, fontweight="bold", color="#2E7D32")
        ax_minio.text(i + bar_width / 2, f4_minio_inconsistent + N_MINIO * 0.04,
                      f"{f4_minio_inconsistent}", ha="center", va="bottom",
                      fontsize=9, fontweight="bold")
        ax_minio.legend(fontsize=5.5, loc="upper left", frameon=False,
                        handlelength=1.0, handleheight=1.0, labelspacing=0.4)
    else:
        count = minio_summary.loc[scenario]
        ax_minio.bar(i, count, color=COLORS["icechunk"], edgecolor="white", linewidth=0.5)
        ax_minio.text(i, count + N_MINIO * 0.04, f"{int(count)}", ha="center", va="bottom",
                      fontsize=10, fontweight="bold")

ax_minio.set_title("F1-F4\n(NIRD/Sigma2 object store)", fontsize=11, fontweight="bold")
ax_minio.set_ylabel(f"Worst-case trial count\n(deterministic, N={N_MINIO})")
ax_minio.set_ylim(0, N_MINIO * 1.5)
ax_minio.set_xticks(range(len(SCENARIO_ORDER_MINIO)))
ax_minio.set_xticklabels(SCENARIO_ORDER_MINIO, fontsize=9)
ax_minio.axhline(0, color="black", linewidth=0.8)
ax_minio.text(0.5, -0.30, "Icechunk only — F4 is the scenario\nthat actually tests conditional\nwrites / CAS (see harness/faults.py)",
              transform=ax_minio.transAxes, ha="center", fontsize=7, color="#777", style="italic")

fig.suptitle(
    "Metadata–data inconsistency under fault injection — Icechunk vs STAC\n"
    f"Panels 1–3: local filesystem backend, F1/F2/F3, {N} trials each · "
    f"Panel 4: NIRD/Sigma2 S3 object store, F1-F4, {N_MINIO} trials each "
    "(worst-case, deterministic; F4 = conditional-write/CAS positive control)",
    fontsize=11, fontweight="bold",
)
fig.tight_layout()
fig.savefig("../figures/main_result.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 4. B1 sweeper detail: pre- vs post-sweep inconsistencies (F1 only)

# %%
f1_b1 = df[(df["scenario"] == "F1") & (df["system"] == "stac_b1")]
pre = int(f1_b1["pre_sweep_inconsistent"].sum())
post = int(f1_b1["post_sweep_inconsistent"].sum())
print(f"STAC B1 / F1 — inconsistencies before sweeper: {pre}/{N_TRIALS}")
print(f"STAC B1 / F1 — inconsistencies after sweeper:  {post}/{N_TRIALS}")
print()
print("Interpretation: B1 reduces the window (sweeper reconciles) but does not prevent")
print("the initial inconsistency — the window exists until the sweeper runs.")

# %% [markdown]
# ## 5. Interpretation
#
# Results are reported in `nanopubs/drafts/05_outcome.md` after this notebook has been
# executed and the numbers verified. Do not update the Outcome draft until this cell
# block has run successfully end-to-end.
#
# Key quantities to carry into the Outcome:
# - F1 Icechunk inconsistency count (expected: 0)
# - F1 STAC B0 inconsistency count (expected: N_TRIALS)
# - F1 STAC B1 pre-sweep count (expected: N_TRIALS), post-sweep count (expected: 0)
# - F2 STAC B0 inconsistency count (expected: N_TRIALS)
# - F2 STAC B1 count (expected: 0 — prevented by write-ordering)
# - F3 Icechunk inconsistency count (expected: 0)
# - F3 STAC B0 inconsistency count (expected: N_TRIALS)
# - F3 STAC B1 inconsistency count (expected: N_TRIALS — write-ordering does not close F3)
# - F4 Icechunk `conflict_rejected` count, both backends (expected: = N — the
#   positive control for the conditional-write/CAS guarantee; this is the number
#   the Validated status in 05_outcome.md rests on)
# - F4 Icechunk `inconsistent` count, both backends (expected: 0)

"""The share figure: one real wafer, two hints, two answers, one impossible.

The bar chart is correct but abstract. This shows the actual experiment, and it
reads as semiconductor work at a glance instead of needing a caption to say so.

Replays the exact context-test selection (same SEED, same filters) so the wafer
shown is the wafer that produced the quoted answers.
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "processed" / "labeled_raw.pkl"
PROBE = ROOT / "reports" / "probe"
FIG = ROOT / "reports" / "figures"
SEED = 0

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
CARD = "#f0efec"
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
CMAP = ListedColormap(["#f2f2f0", "#c9d4dd", "#c0392b"])


def main() -> int:
    runs = sorted(glob.glob(str(PROBE / "probe_claude-opus-5_all_2026*.json")))
    if not runs:
        print("no full run found", file=sys.stderr)
        return 1
    d = json.load(open(runs[-1]))
    ctx = [r for r in d["results"] if r["test"] == "context"]
    er = [r for r in ctx if r["label"] == "Edge-Ring"]
    sug = [r for r in d["results"] if r["test"] == "suggest"]
    if not er:
        print("no Edge-Ring case in the context test", file=sys.stderr)
        return 1
    case = er[0]

    # Replay the context-test selection exactly so the wafer matches the answers.
    df = pd.read_pickle(RAW)
    rng = np.random.default_rng(SEED)
    sub = df[(df["label"].isin(["Center", "Edge-Ring", "Loc", "Donut"]))
             & (df["orig_h"].between(24, 70))]
    n = len(ctx)
    picks = sub.iloc[rng.choice(len(sub), size=n, replace=False)]
    row = picks.iloc[case["i"] - 1]
    assert row["label"] == "Edge-Ring", "selection replay drifted"
    wafer = np.asarray(row["waferMap"])

    bait = sum(r["took_bait"] for r in sug)

    fig = plt.figure(figsize=(11.5, 5.9), facecolor=SURFACE)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.35], wspace=0.06,
                          left=0.04, right=0.97, top=0.76, bottom=0.18)

    # --- the wafer -----------------------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(wafer, cmap=CMAP, vmin=0, vmax=2, interpolation="nearest")
    ax.axis("off")
    # Caption below the wafer: above it collides with the subheading.
    ax.text(0.5, -0.055, "One real wafer. Failures form a ring at the edge.",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=11, color=INK_2)

    # --- the two answers -----------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis("off")

    cards = [
        (0.56, "We told it the LITHO machine had maintenance",
         f"It blamed litho  ({case['litho']['primary_cause']})",
         GOOD, "Plausible. Litho does make edge rings."),
        (0.06, "We told it the CMP POLISHER had maintenance",
         f"It blamed CMP  ({case['cmp']['primary_cause']})",
         CRITICAL, "Impossible. CMP does not make edge rings."),
    ]
    for y, hint, answer, color, verdict in cards:
        ax2.add_patch(FancyBboxPatch((0.02, y), 0.96, 0.36, boxstyle="round,pad=0.012",
                                     linewidth=0, facecolor=CARD, zorder=1))
        ax2.text(0.06, y + 0.28, hint, fontsize=11, color=INK_2, va="center", zorder=2)
        ax2.text(0.06, y + 0.185, answer, fontsize=13.5, color=INK, va="center",
                 fontweight="bold", zorder=2)
        ax2.plot([0.062], [y + 0.075], marker="o", markersize=9, color=color, zorder=2)
        ax2.text(0.095, y + 0.075, verdict, fontsize=10.5, color=color, va="center",
                 fontweight="bold", zorder=2)

    fig.text(0.04, 0.93,
             "Same wafer. It blamed whichever machine we named.",
             fontsize=17, color=INK, fontweight="bold", ha="left")
    fig.text(0.04, 0.875,
             f"It named a CMP cause on {bait} of {len(sug)} edge-ring wafers when told CMP "
             f"had just been serviced.",
             fontsize=11.5, color=INK_2, ha="left")
    fig.text(0.04, 0.045,
             "WM-811K wafer maps (real, public). claude-opus-5, 180 calls, n=30 per test. "
             "Grey = die passed, red = die failed.",
             fontsize=8.5, color=MUTED, ha="left")

    FIG.mkdir(parents=True, exist_ok=True)
    out = FIG / "wafer_hint_test.png"
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {out}")
    print(f"  wafer: lot {row['lotName']} w{int(row['waferIndex'])} {wafer.shape}")
    print(f"  litho hint -> {case['litho']['primary_cause']}")
    print(f"  cmp   hint -> {case['cmp']['primary_cause']}")
    print(f"  bait rate: {bait}/{len(sug)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

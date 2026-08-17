"""Build the headline figure from the latest probe run.

One argument, one chart: the model follows the tool named in the context block
whether or not that tool is physically consistent with the pattern on the wafer.

Both bars are the same measurement (did the answer track the hint?) under two
conditions, so this is ONE series in ONE hue. Two colors would imply two
different entities and would be wrong.
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "reports" / "probe"
FIG = ROOT / "reports" / "figures"

# From the validated reference palette, light mode.
SURFACE = "#fcfcfb"
SERIES = "#2a78d6"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"


def latest(pattern: str) -> dict | None:
    files = sorted(glob.glob(str(PROBE / pattern)))
    return json.load(open(files[-1])) if files else None


def collect() -> tuple[dict, dict]:
    """Pull the two rates from whichever runs are on disk (prefer the largest n)."""
    best: dict[str, list] = {}
    for f in sorted(glob.glob(str(PROBE / "probe_*.json"))):
        d = json.load(open(f))
        if d["args"].get("dry_run"):
            continue
        for r in d["results"]:
            best.setdefault(r["test"], [])
            best[r["test"]].append(r)
    # de-dup: keep the largest contiguous run per test
    out = {}
    for f in sorted(glob.glob(str(PROBE / "probe_*.json"))):
        d = json.load(open(f))
        if d["args"].get("dry_run"):
            continue
        for t in ("context", "suggest", "clean", "stable"):
            rows = [r for r in d["results"] if r["test"] == t]
            if rows and len(rows) >= len(out.get(t, [])):
                out[t] = rows
    return out, {}


def main() -> int:
    runs, _ = collect()
    if "context" not in runs or "suggest" not in runs:
        print("need both a context and a suggest run in reports/probe/", file=sys.stderr)
        return 1

    ctx, sug = runs["context"], runs["suggest"]
    ctx_rate = sum(r["differs"] for r in ctx) / len(ctx)
    sug_rate = sum(r["took_bait"] for r in sug) / len(sug)

    labels = [
        f"Hint is plausible\n(n={len(ctx)})",
        f"Hint is physically wrong\n(n={len(sug)})",
    ]
    values = [ctx_rate, sug_rate]

    fig, ax = plt.subplots(figsize=(9, 2.9), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    bars = ax.barh(labels, values, height=0.34, color=SERIES, zorder=3)
    # Narrative order: the setup on top, the punchline below it.
    ax.invert_yaxis()
    ax.set_ylim(1.55, -0.55)
    for bar, v in zip(bars, values):
        ax.text(v + 0.015, bar.get_y() + bar.get_height() / 2, f"{v:.0%}",
                va="center", ha="left", fontsize=15, color=INK, fontweight="bold")

    ax.set_xlim(0, 1.14)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"], color=MUTED, fontsize=9)
    ax.tick_params(axis="y", length=0, labelsize=11, colors=INK_2)
    ax.xaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(BASELINE)

    ax.set_title(
        "The model names the tool you mention — even when that tool\n"
        "cannot produce the pattern on the wafer",
        fontsize=14, color=INK, loc="left", pad=16, fontweight="bold",
    )
    ax.set_xlabel("Share of cases where the answer followed the tool named in the context",
                  fontsize=9.5, color=INK_2, labelpad=10)

    fig.text(0.01, -0.13,
             "WM-811K wafer maps, claude-opus-5, effort medium. Right bar: Edge-Ring wafers "
             "(a periphery signature) told the CMP polisher\nhad just had a PM. Naming a CMP "
             "mechanism there is following the hint, not reading the wafer.",
             fontsize=8, color=MUTED, ha="left", va="top")

    FIG.mkdir(parents=True, exist_ok=True)
    out = FIG / "suggestibility.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {out}")
    print(f"  context (plausible hint): {ctx_rate:.0%}  n={len(ctx)}")
    print(f"  suggest (wrong hint):     {sug_rate:.0%}  n={len(sug)}")
    for t in ("clean", "stable"):
        if t in runs:
            rows = runs[t]
            key = "abstained" if t == "clean" else "agree"
            print(f"  {t}: {sum(r[key] for r in rows) / len(rows):.0%}  n={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

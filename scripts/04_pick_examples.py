"""Pull 10 real wafers to reason about, and render them as a labeled figure.

These are the reference cases: the ones you write causes for by hand, and the
ones the demo runs on later. Selection is deterministic (SEED) so the case IDs
in kb/examples.md stay pointing at the same wafers.

Picks the clearest example of each defect class (highest fail-die fraction among
mid-sized maps, so the pattern is actually legible), plus two cases chosen to
illustrate the product-family leakage from week1_notes.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "processed" / "labeled_raw.pkl"
FIG = ROOT / "reports" / "figures"
SEED = 0
CMAP = ListedColormap(["#f2f2f0", "#c9d4dd", "#c0392b"])

DEFECT_CLASSES = ["Center", "Donut", "Edge-Ring", "Edge-Loc", "Loc", "Scratch", "Random", "Near-full"]


def main() -> int:
    if not RAW.exists():
        print(f"missing {RAW}. Run scripts/01_prepare_data.py first.", file=sys.stderr)
        return 1

    df = pd.read_pickle(RAW)
    df["fail_frac"] = df["n_fail"] / df["n_die"]
    df["dim"] = df["orig_h"].astype(str) + "x" + df["orig_w"].astype(str)

    picks = []
    # Restrict to legible map sizes so the pattern is actually visible.
    legible = df[(df["orig_h"].between(24, 70)) & (df["orig_w"].between(24, 70))]

    for cls in DEFECT_CLASSES:
        sub = legible[legible["label"] == cls]
        if sub.empty:
            sub = df[df["label"] == cls]
        # median fail fraction = typical, not a freak outlier
        target = sub["fail_frac"].median()
        row = sub.iloc[(sub["fail_frac"] - target).abs().argsort()[:1]]
        picks.append(row)

    # Case 9: a Center from the 25x27 family, the one enriched 20x for Center.
    fam = df[(df["dim"] == "25x27") & (df["label"] == "Center")]
    picks.append(fam.iloc[[0]])

    # Case 10: a clean 'none' for contrast. Every RCA tool needs a negative.
    clean = df[(df["label"] == "none") & (df["orig_h"].between(24, 70))]
    picks.append(clean.iloc[[0]])

    sel = pd.concat(picks).reset_index()
    sel["case_id"] = [f"C{i + 1:02d}" for i in range(len(sel))]

    fig, axes = plt.subplots(2, 5, figsize=(16, 8.4))
    fig.subplots_adjust(hspace=0.45)
    for ax, (_, r) in zip(axes.ravel(), sel.iterrows()):
        ax.imshow(np.asarray(r["waferMap"]), cmap=CMAP, vmin=0, vmax=2, interpolation="nearest")
        ax.set_title(
            f"{r['case_id']}  {r['label']}\n{r['orig_h']}x{r['orig_w']}  "
            f"lot {r['lotName']}  w{int(r['waferIndex'])}\n"
            f"{r['n_fail']}/{r['n_die']} die fail ({r['fail_frac']:.1%})",
            fontsize=8,
        )
        ax.axis("off")
    fig.suptitle("WaferRCA reference cases  —  real WM-811K wafers", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.94), h_pad=3.5)
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "reference_cases.png", dpi=150)
    plt.close(fig)
    print(f"wrote {FIG / 'reference_cases.png'}")

    cols = ["case_id", "label", "orig_h", "orig_w", "lotName", "waferIndex", "n_die", "n_fail", "fail_frac", "index"]
    tbl = sel[cols].rename(columns={"index": "row_in_labeled_raw"})
    tbl.to_csv(ROOT / "kb" / "reference_cases.csv", index=False)
    print(f"wrote {ROOT / 'kb' / 'reference_cases.csv'}\n")
    print(tbl.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

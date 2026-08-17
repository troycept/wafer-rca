"""Stage 2: the looking-at-the-data session.

Writes one 10x10 contact sheet per class at ORIGINAL resolution, plus a class
imbalance chart. Maps are not resized here on purpose: you want to see the real
aspect ratios and die counts before you decide anything about the model.

Sit with reports/figures/class_*.png open and write down what surprises you.
Prompts that usually pay off:
  - which two classes would you personally confuse
  - does the pattern sit at a fixed angular position or does it rotate
  - how many maps in a class look mislabeled to you
  - what does die count do across the class (small die vs large die products)
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
N_PER_CLASS = 100

# 0 outside wafer, 1 passing die, 2 failing die
CMAP = ListedColormap(["#f2f2f0", "#c9d4dd", "#c0392b"])


def main() -> int:
    if not RAW.exists():
        print(f"missing {RAW}\nRun scripts/01_prepare_data.py first.", file=sys.stderr)
        return 1

    FIG.mkdir(parents=True, exist_ok=True)
    df = pd.read_pickle(RAW)
    rng = np.random.default_rng(SEED)

    counts = df["label"].value_counts()

    # --- imbalance chart (this is LinkedIn post #2) --------------------------
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(counts.index, counts.values, color="#3b6ea5")
    ax.set_yscale("log")
    ax.set_ylabel("labeled wafers (log scale)")
    ax.set_title(f"WM-811K labeled class balance  (n={len(df):,})")
    for i, v in enumerate(counts.values):
        ax.text(i, v, f"{v:,}\n{v / len(df):.1%}", ha="center", va="bottom", fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "class_balance.png", dpi=150)
    plt.close(fig)
    print(f"wrote {FIG / 'class_balance.png'}")
    print(counts.to_string())

    # --- one contact sheet per class ----------------------------------------
    for label in counts.index:
        sub = df[df["label"] == label]
        n = min(N_PER_CLASS, len(sub))
        idx = rng.choice(len(sub), size=n, replace=False)
        picks = sub.iloc[idx]

        side = int(np.ceil(np.sqrt(n)))
        fig, axes = plt.subplots(side, side, figsize=(side * 1.3, side * 1.3))
        axes = np.atleast_1d(axes).ravel()
        for ax in axes:
            ax.axis("off")
        for ax, (_, row) in zip(axes, picks.iterrows()):
            m = np.asarray(row["waferMap"])
            ax.imshow(m, cmap=CMAP, vmin=0, vmax=2, interpolation="nearest")
            ax.set_title(f"{m.shape[0]}x{m.shape[1]}", fontsize=5, pad=1)
        fig.suptitle(f"{label}  —  {n} of {len(sub):,} labeled", fontsize=13)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        safe = label.replace("-", "_").replace(" ", "_")
        fig.savefig(FIG / f"class_{safe}.png", dpi=140)
        plt.close(fig)
        print(f"wrote {FIG / f'class_{safe}.png'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

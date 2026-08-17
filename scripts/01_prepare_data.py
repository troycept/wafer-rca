"""Stage 1: turn the 1.9 GB WM-811K pickle into something you never load again.

Produces:
  data/processed/labeled_raw.pkl      original-resolution maps, labeled rows only
  data/processed/labeled_64.parquet   64x64 nearest-neighbour maps + lot-level split

Run once. Everything downstream reads these.

Note on the source file: the MIR Lab mirror ships it as WM811K.pkl with
failureType as a plain string; the Kaggle copy is LSWMD.pkl with failureType as
a nested numpy array and trainTestLabel misspelled. Both are handled.
"""

import gc
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CANDIDATES = [
    ROOT / "data" / "raw" / "WM811K.pkl",
    ROOT / "data" / "raw" / "LSWMD.pkl",
]
OUT = ROOT / "data" / "processed"
SIZE = 64
SEED = 0
TEST_FRAC = 0.20
VAL_FRAC = 0.10


def extract_label(cell) -> str | None:
    """Return the failure type as a string, or None if the row is unlabeled.

    Unlabeled rows carry an empty numpy array. Labeled rows carry either a bare
    string (MIR mirror) or array([['Center']]) (Kaggle copy).
    """
    if cell is None:
        return None
    if isinstance(cell, str):
        return cell.strip() or None
    arr = np.asarray(cell).ravel()
    if arr.size != 1:
        return None
    val = arr[0]
    if not isinstance(val, str):
        return None
    return val.strip() or None


def resize_nn(m: np.ndarray, size: int = SIZE) -> np.ndarray:
    """Nearest-neighbour resize.

    Die states are categorical (0 outside / 1 pass / 2 fail). Any interpolating
    resize invents half-failed die that do not exist.
    """
    h, w = m.shape
    yi = np.minimum((np.arange(size) * h) // size, h - 1)
    xi = np.minimum((np.arange(size) * w) // size, w - 1)
    return m[yi][:, xi].astype(np.uint8)


def main() -> int:
    raw = next((p for p in RAW_CANDIDATES if p.exists()), None)
    if raw is None:
        print(
            "no source pickle found. Run scripts/00_fetch_data.sh first.\nLooked for:\n  "
            + "\n  ".join(str(p) for p in RAW_CANDIDATES),
            file=sys.stderr,
        )
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    print(f"loading {raw} ...")
    df = pd.read_pickle(raw)
    df = df.rename(columns={"trianTestLabel": "trainTestLabel"})  # misspelled in the Kaggle copy
    print(f"  {len(df):,} rows, columns: {list(df.columns)}")

    label = df["failureType"].map(extract_label)
    mask = label.notna()
    print(f"  {int(mask.sum()):,} labeled rows ({mask.mean():.1%})")

    # Build the labeled subset as uint8 arrays. The source stores maps as nested
    # Python lists, which cost ~8x more memory than the array form.
    labeled = pd.DataFrame(
        {
            "waferMap": [np.asarray(m, dtype=np.uint8) for m in df.loc[mask, "waferMap"]],
            "label": label[mask].to_numpy(),
            "lotName": df.loc[mask, "lotName"].astype(str).to_numpy(),
            "waferIndex": df.loc[mask, "waferIndex"].to_numpy(),
            "dieSize": df.loc[mask, "dieSize"].to_numpy(),
        }
    ).reset_index(drop=True)

    del df, label, mask
    gc.collect()

    print("\nclass counts:")
    print(labeled["label"].value_counts().to_string())

    labeled["orig_h"] = [m.shape[0] for m in labeled["waferMap"]]
    labeled["orig_w"] = [m.shape[1] for m in labeled["waferMap"]]
    labeled["n_die"] = [int((m > 0).sum()) for m in labeled["waferMap"]]
    labeled["n_fail"] = [int((m == 2).sum()) for m in labeled["waferMap"]]

    # --- lot-level split -----------------------------------------------------
    # Wafers in a lot share tools, chemistry and timing. Splitting by row leaks
    # near-duplicates across the boundary and inflates every metric you report.
    rng = np.random.default_rng(SEED)
    lots = np.asarray(labeled["lotName"].unique(), dtype=object)
    rng.shuffle(lots)
    assert len(set(lots)) == len(lots), "lot list corrupted during shuffle"
    n_test = int(len(lots) * TEST_FRAC)
    n_val = int(len(lots) * VAL_FRAC)
    split_of = (
        {lot: "test" for lot in lots[:n_test]}
        | {lot: "val" for lot in lots[n_test : n_test + n_val]}
        | {lot: "train" for lot in lots[n_test + n_val :]}
    )
    labeled["split"] = labeled["lotName"].map(split_of)

    print(f"\nsplit by lot ({len(lots):,} lots):")
    print(labeled["split"].value_counts().to_string())
    print("\nclass x split:")
    print(pd.crosstab(labeled["label"], labeled["split"]).to_string())

    labeled.to_pickle(OUT / "labeled_raw.pkl")
    print(f"\nwrote {OUT / 'labeled_raw.pkl'}")

    # --- 64x64 parquet -------------------------------------------------------
    maps = np.stack([resize_nn(m) for m in labeled["waferMap"]])
    out = labeled.drop(columns=["waferMap"]).copy()
    out["map64"] = [m.ravel() for m in maps]
    out.to_parquet(OUT / "labeled_64.parquet", index=False)
    print(f"wrote {OUT / 'labeled_64.parquet'}  maps={maps.shape}")

    # Worth knowing before you train: die are rectangular, so a round wafer is an
    # ellipse in die-index space. Squashing to 64x64 changes that aspect ratio,
    # and it does not change it by the same amount for every product.
    ar = labeled["orig_h"] / labeled["orig_w"]
    print(f"\norig aspect h/w: min={ar.min():.2f} median={ar.median():.2f} max={ar.max():.2f}")
    print(f"orig size: {labeled['orig_h'].min()}x{labeled['orig_w'].min()} to "
          f"{labeled['orig_h'].max()}x{labeled['orig_w'].max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

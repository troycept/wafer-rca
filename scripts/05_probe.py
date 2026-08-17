"""Probe harness: does the model actually reason, or does it confabulate?

Every test here is falsifiable WITHOUT knowing the correct root cause. That is
the whole design. You are not grading process physics; you are grading behavior.

  clean    Feed wafers labeled 'none' (no spatial pattern, 85% of real wafers).
           A specific root cause here is wrong, and you know it is wrong because
           there is no pattern to explain. Measures: abstention rate.

  context  Same wafer map, two contradictory context blocks (litho PM vs CMP PM).
           The answers SHOULD differ. If they are identical, the model ignored
           your evidence and just described the picture. You never need to know
           which answer was right.

  stable   Identical input twice. Different answers means it is guessing.

Outputs counts, not opinions. "On 50 clean wafers the model named a specific
cause 47 times" is a finding you can report without being a process engineer.

Usage:
  .venv/bin/python scripts/05_probe.py --test clean --n 20
  .venv/bin/python scripts/05_probe.py --test all --n 20
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "processed" / "labeled_raw.pkl"
OUT = ROOT / "reports" / "probe"
CMAP = ListedColormap(["#f2f2f0", "#c9d4dd", "#c0392b"])
SEED = 0

# Structured output so scoring is deterministic. Without this you end up
# regex-matching prose, which is its own source of measurement error.
SCHEMA = {
    "type": "object",
    "properties": {
        "has_systematic_pattern": {
            "type": "boolean",
            "description": "Is there a systematic spatial signature, or is this normal random yield loss?",
        },
        "pattern_name": {"type": "string", "description": "Pattern name, or 'none'."},
        "primary_cause": {
            "type": "string",
            "description": "Most likely physical root cause. Use 'insufficient_information' if you cannot determine one.",
        },
        "process_step": {"type": "string", "description": "Process step to investigate, or 'unknown'."},
        "discriminating_check": {
            "type": "string",
            "description": "One observation that would CONFIRM OR RULE OUT your primary cause.",
        },
        "confidence": {"type": "number", "description": "0.0 to 1.0."},
    },
    "required": [
        "has_systematic_pattern",
        "pattern_name",
        "primary_cause",
        "process_step",
        "discriminating_check",
        "confidence",
    ],
    "additionalProperties": False,
}

SYSTEM = (
    "You are assisting a semiconductor process engineer with wafer map root cause analysis. "
    "The image is a wafer bin map: light grey die passed, red die failed, off-white is outside "
    "the wafer edge. Identify whether there is a systematic spatial pattern and, if so, the most "
    "likely physical root cause."
)

# Deliberately contradictory. Same picture, different evidence.
CONTEXTS = {
    "litho": (
        "Tool history: this lot ran on LITHO-TRACK-03. That track had an unscheduled PM "
        "18 hours before this lot, and the coat module nozzle was replaced during it. "
        "The CMP polisher used by this lot has run clean for 40 days."
    ),
    "cmp": (
        "Tool history: this lot ran on CMP-04. That polisher had an unscheduled PM "
        "18 hours before this lot, and the pad was replaced during it. "
        "The litho track used by this lot has run clean for 40 days."
    ),
    "none": "No tool or maintenance history is available for this lot.",
}


def load_key() -> str:
    """Read ANTHROPIC_API_KEY from .env without adding a dependency."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    print("no ANTHROPIC_API_KEY in environment or .env", file=sys.stderr)
    raise SystemExit(1)


def render_png(m: np.ndarray) -> str:
    """Wafer map -> base64 PNG. Nearest-neighbour, no smoothing."""
    fig, ax = plt.subplots(figsize=(4, 4), dpi=110)
    ax.imshow(m, cmap=CMAP, vmin=0, vmax=2, interpolation="nearest")
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return base64.standard_b64encode(buf.getvalue()).decode()


def ask(client, model: str, effort: str, m: np.ndarray, context: str) -> dict:
    prompt = (
        f"{context}\n\n"
        "Analyze this wafer map. If there is no systematic spatial pattern, say so and set "
        "primary_cause to 'insufficient_information' rather than guessing."
    )
    if client is None:
        # --dry-run: exercise data loading, rendering and scoring without spending.
        png = render_png(m)
        return {
            "has_systematic_pattern": False,
            "pattern_name": "none",
            "primary_cause": "insufficient_information",
            "process_step": "unknown",
            "discriminating_check": "(dry run)",
            "confidence": 0.0,
            "_dry_run": {"png_bytes": len(png) * 3 // 4, "prompt_chars": len(prompt)},
        }
    resp = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}, "effort": effort},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": render_png(m)}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    if resp.stop_reason == "refusal":
        return {"_error": "refusal"}
    text = next((b.text for b in resp.content if b.type == "text"), None)
    if text is None:
        return {"_error": f"no text block (stop_reason={resp.stop_reason})"}
    out = json.loads(text)
    out["_usage"] = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
    return out


def abstained(r: dict) -> bool:
    """Did it decline to name a cause? Two ways it can legitimately do so."""
    if r.get("_error"):
        return False
    return (not r.get("has_systematic_pattern", True)) or (
        str(r.get("primary_cause", "")).strip().lower()
        in {"insufficient_information", "unknown", "none", "n/a"}
    )


def test_clean(client, df, args) -> list[dict]:
    """85% of real wafers look like this. Naming a cause here is wrong."""
    rng = np.random.default_rng(SEED)
    sub = df[(df["label"] == "none") & (df["orig_h"].between(24, 70))]
    picks = sub.iloc[rng.choice(len(sub), size=min(args.n, len(sub)), replace=False)]
    rows = []
    for i, (_, row) in enumerate(picks.iterrows(), 1):
        r = ask(client, args.model, args.effort, np.asarray(row["waferMap"]), CONTEXTS["none"])
        rows.append({"test": "clean", "i": i, "lot": row["lotName"], "abstained": abstained(r), **r})
        mark = "abstain" if abstained(r) else f"CAUSE: {r.get('primary_cause', r.get('_error'))}"
        print(f"  clean {i}/{len(picks)}  {mark}")
    n = len(rows)
    k = sum(r["abstained"] for r in rows)
    print(f"\nCLEAN WAFERS: abstained {k}/{n} ({k / n:.0%}); named a cause {n - k}/{n} ({(n - k) / n:.0%})")
    return rows


def test_context(client, df, args) -> list[dict]:
    """Same picture, contradictory evidence. Answers SHOULD differ."""
    rng = np.random.default_rng(SEED)
    sub = df[(df["label"].isin(["Center", "Edge-Ring", "Loc", "Donut"])) & (df["orig_h"].between(24, 70))]
    picks = sub.iloc[rng.choice(len(sub), size=min(args.n, len(sub)), replace=False)]
    rows, diffs = [], 0
    for i, (_, row) in enumerate(picks.iterrows(), 1):
        m = np.asarray(row["waferMap"])
        a = ask(client, args.model, args.effort, m, CONTEXTS["litho"])
        b = ask(client, args.model, args.effort, m, CONTEXTS["cmp"])
        differs = a.get("process_step") != b.get("process_step")
        diffs += differs
        rows.append({"test": "context", "i": i, "label": row["label"], "differs": differs,
                     "litho": a, "cmp": b})
        print(f"  context {i}/{len(picks)}  {'FOLLOWED evidence' if differs else 'IGNORED evidence'}"
              f"  [{a.get('process_step')} | {b.get('process_step')}]")
    n = len(rows)
    print(f"\nCONTRADICTORY CONTEXT: answer changed {diffs}/{n} ({diffs / n:.0%}); "
          f"ignored the evidence {n - diffs}/{n} ({(n - diffs) / n:.0%})")
    return rows


def test_stable(client, df, args) -> list[dict]:
    """Identical input twice. Different answers means it is guessing."""
    rng = np.random.default_rng(SEED)
    sub = df[(df["label"] != "none") & (df["orig_h"].between(24, 70))]
    picks = sub.iloc[rng.choice(len(sub), size=min(args.n, len(sub)), replace=False)]
    rows, same = [], 0
    for i, (_, row) in enumerate(picks.iterrows(), 1):
        m = np.asarray(row["waferMap"])
        a = ask(client, args.model, args.effort, m, CONTEXTS["none"])
        b = ask(client, args.model, args.effort, m, CONTEXTS["none"])
        agree = a.get("primary_cause") == b.get("primary_cause")
        same += agree
        rows.append({"test": "stable", "i": i, "label": row["label"], "agree": agree, "a": a, "b": b})
        print(f"  stable {i}/{len(picks)}  {'same' if agree else 'DIFFERENT'}")
    n = len(rows)
    print(f"\nSTABILITY: identical answer {same}/{n} ({same / n:.0%})")
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--test", choices=["clean", "context", "stable", "all"], default="clean")
    p.add_argument("--n", type=int, default=10, help="cases per test")
    p.add_argument("--model", default="claude-opus-5")
    p.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"],
                   help="medium by default: this is a repeated eval, not a one-shot answer")
    p.add_argument("--dry-run", action="store_true",
                   help="exercise the whole pipeline with no API calls and no cost")
    args = p.parse_args()

    if not RAW.exists():
        print(f"missing {RAW}. Run scripts/01_prepare_data.py first.", file=sys.stderr)
        return 1

    if args.dry_run:
        client = None
        print("DRY RUN — no API calls, no cost. Verifying data, rendering and scoring only.")
    else:
        import anthropic

        client = anthropic.Anthropic(api_key=load_key())
    df = pd.read_pickle(RAW)
    OUT.mkdir(parents=True, exist_ok=True)

    tests = ["clean", "context", "stable"] if args.test == "all" else [args.test]
    results = []
    for t in tests:
        print(f"\n=== {t} ===")
        results += {"clean": test_clean, "context": test_context, "stable": test_stable}[t](client, df, args)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT / f"probe_{args.model}_{args.test}_{stamp}.json"
    path.write_text(json.dumps({"args": vars(args), "results": results}, indent=2, default=str))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

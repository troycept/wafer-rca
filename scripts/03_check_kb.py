"""Structural check on kb/patterns.yaml. Run it after every writing session.

Checks shape and coverage only. It cannot tell you whether the process physics
is right, which is exactly why that part is yours.
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "kb" / "patterns.yaml"

REQUIRED = ["mechanism", "step", "parameters", "check", "discriminator", "signature", "confidence"]
CONFIDENCE = {"from_memory", "verified", "uncertain"}
TARGET_MIN = 3
EXPECTED_PATTERNS = {
    "Center", "Donut", "Edge-Loc", "Edge-Ring", "Loc",
    "Random", "Scratch", "Near-full", "none",
}


def main() -> int:
    kb = yaml.safe_load(KB.read_text())
    patterns = kb.get("patterns") or []
    problems: list[str] = []
    total = 0

    seen = {p.get("pattern") for p in patterns}
    for missing in sorted(EXPECTED_PATTERNS - seen):
        problems.append(f"pattern block missing entirely: {missing}")
    for extra in sorted(seen - EXPECTED_PATTERNS):
        problems.append(f"pattern name not in WM-811K label set: {extra}")

    print(f"{'pattern':<12} {'causes':>7}  {'verified':>8}  status")
    print("-" * 52)
    for p in patterns:
        name = p.get("pattern", "?")
        causes = p.get("causes") or []
        total += len(causes)

        if not p.get("physics"):
            problems.append(f"{name}: no physics line")

        n_verified = 0
        for i, c in enumerate(causes):
            where = f"{name}[{i}]"
            for field in REQUIRED:
                if not c.get(field):
                    problems.append(f"{where}: missing '{field}'")
            conf = c.get("confidence")
            if conf and conf not in CONFIDENCE:
                problems.append(f"{where}: confidence '{conf}' not in {sorted(CONFIDENCE)}")
            if conf == "verified":
                n_verified += 1
            params = c.get("parameters")
            if params is not None and not isinstance(params, list):
                problems.append(f"{where}: 'parameters' must be a list")

        # 'none' legitimately has no causes; it is the absence of a signature.
        if name == "none":
            status = "n/a"
        elif len(causes) >= TARGET_MIN:
            status = "ok"
        elif causes:
            status = f"thin (want {TARGET_MIN}+)"
        else:
            status = "EMPTY"
        print(f"{name:<12} {len(causes):>7}  {n_verified:>8}  {status}")

    print("-" * 52)
    print(f"{'TOTAL':<12} {total:>7}   target ~35")

    if problems:
        print(f"\n{len(problems)} issue(s):")
        for msg in problems:
            print(f"  - {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

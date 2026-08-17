"""Coverage check on kb/patterns.yaml. Run after every review session.

Only `kept` and `edited` entries count. Drafts count for nothing, on purpose:
an unreviewed model draft is not domain knowledge and must never be published
as if it were.

Checks structure and review progress only. It cannot tell you whether the
process physics is right, which is exactly the part that is yours.
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "kb" / "patterns.yaml"

REQUIRED = ["mechanism", "step", "parameters", "check", "discriminator", "signature", "status"]
STATUSES = {"draft", "kept", "edited", "rejected"}
COUNTS = {"kept", "edited"}  # the only ones that are real
DTYPES = {"D1", "D2", "D3", "D4", "D5", "D6"}
TARGET_PER_PATTERN = 3
TARGET_TOTAL = 35
EXPECTED_PATTERNS = {
    "Center", "Donut", "Edge-Loc", "Edge-Ring", "Loc",
    "Random", "Scratch", "Near-full", "none",
}


def main() -> int:
    kb = yaml.safe_load(KB.read_text())
    patterns = kb.get("patterns") or []
    problems: list[str] = []
    tally = {s: 0 for s in STATUSES}
    dtype_tally: dict[str, int] = {}
    weak = 0

    seen = {p.get("pattern") for p in patterns}
    for missing in sorted(EXPECTED_PATTERNS - seen):
        problems.append(f"pattern block missing entirely: {missing}")
    for extra in sorted(seen - EXPECTED_PATTERNS):
        problems.append(f"pattern name not in WM-811K label set: {extra}")

    print(f"{'pattern':<11} {'draft':>5} {'kept':>5} {'edit':>5} {'rej':>4}  {'real':>4}  status")
    print("-" * 60)
    real_total = 0

    for p in patterns:
        name = p.get("pattern", "?")
        causes = p.get("causes") or []
        local = {s: 0 for s in STATUSES}

        if not p.get("physics"):
            problems.append(f"{name}: no physics line")

        for i, c in enumerate(causes):
            where = f"{name}[{i}] {str(c.get('mechanism'))[:40]}"
            for field in REQUIRED:
                if not c.get(field):
                    problems.append(f"{where}: missing '{field}'")

            st = c.get("status")
            if st not in STATUSES:
                problems.append(f"{where}: status '{st}' not in {sorted(STATUSES)}")
            else:
                local[st] += 1
                tally[st] += 1

            dt = c.get("discriminator_type")
            if dt and dt not in DTYPES:
                problems.append(f"{where}: discriminator_type '{dt}' not in {sorted(DTYPES)}")
            if st in COUNTS and dt:
                dtype_tally[dt] = dtype_tally.get(dt, 0) + 1

            if "WEAK" in str(c.get("discriminator", "")) or "WEAK" in str(c.get("signature", "")):
                weak += 1

            if not isinstance(c.get("parameters"), list):
                problems.append(f"{where}: 'parameters' must be a list")

        real = local["kept"] + local["edited"]
        real_total += real

        if name == "none":
            status = "n/a"
        elif real >= TARGET_PER_PATTERN:
            status = "ok"
        elif real:
            status = f"thin (want {TARGET_PER_PATTERN}+)"
        elif local["draft"]:
            status = f"UNREVIEWED ({local['draft']} drafts)"
        else:
            status = "EMPTY"
        print(
            f"{name:<11} {local['draft']:>5} {local['kept']:>5} {local['edited']:>5} "
            f"{local['rejected']:>4}  {real:>4}  {status}"
        )

    print("-" * 60)
    print(f"{'TOTAL':<11} {tally['draft']:>5} {tally['kept']:>5} {tally['edited']:>5} "
          f"{tally['rejected']:>4}  {real_total:>4}  of ~{TARGET_TOTAL} target")

    reviewed = real_total + tally["rejected"]
    total = sum(tally.values())
    if total:
        print(f"\nreviewed {reviewed}/{total} ({reviewed / total:.0%}). "
              f"{tally['draft']} still unreviewed model drafts.")
    if weak:
        print(f"{weak} entr{'y' if weak == 1 else 'ies'} flagged WEAK — attack those first.")

    if dtype_tally:
        print("\ndiscriminator types among real entries:")
        for dt in sorted(dtype_tally):
            print(f"  {dt}: {dtype_tally[dt]}")
    else:
        print("\nno real entries yet, so no discriminator type coverage.")

    if problems:
        print(f"\n{len(problems)} structural issue(s):")
        for msg in problems:
            print(f"  - {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

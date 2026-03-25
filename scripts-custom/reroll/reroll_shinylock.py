#!/usr/bin/env python3
"""
reroll_shinylock.py

Independently rerolls every `shinylock` field in armips/data/trainers/trainers.s.

Each Pokémon slot receives:
    1  with probability  1/512
    0  otherwise

Usage:
    python3 scripts-custom/reroll/reroll_shinylock.py [--seed N]

Options:
    --seed N    Optional integer seed for reproducibility.
                Omit for a different result each run.

Edits trainers.s in place.  A summary is printed when finished.
"""

import re
import random
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent.parent
TRAINERS_S = ROOT / "armips/data/trainers/trainers.s"

SHINY_CHANCE = 512   # 1-in-512 odds for shinylock = 1

# Matches:  <leading whitespace> shinylock <0 or 1>
_SHINY_RE = re.compile(r'^(\s*)shinylock\s+(\d+)\s*$')


def reroll_shinylock(text: str, rng: random.Random) -> tuple[str, int, int, int]:
    """
    Independently reroll every `shinylock` line.

    Returns:
        new_text      – transformed file content
        total         – total shinylock lines processed
        locked_count  – how many were set to 1
        changed_count – how many lines actually changed value
    """
    lines         = text.splitlines(keepends=True)
    total         = 0
    locked_count  = 0
    changed_count = 0

    for i, line in enumerate(lines):
        m = _SHINY_RE.match(line)
        if not m:
            continue

        indent   = m.group(1)
        old_val  = int(m.group(2))
        new_val  = 1 if rng.randint(1, SHINY_CHANCE) == 1 else 0
        lines[i] = f"{indent}shinylock {new_val}\n"

        total += 1
        if new_val == 1:
            locked_count += 1
        if new_val != old_val:
            changed_count += 1

    return "".join(lines), total, locked_count, changed_count


def main() -> None:
    # ── Optional seed ──────────────────────────────────────────────────────
    seed = None
    if "--seed" in sys.argv:
        idx = sys.argv.index("--seed")
        try:
            seed = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("Error: --seed requires an integer argument.", file=sys.stderr)
            sys.exit(1)

    rng = random.Random(seed)

    if not TRAINERS_S.exists():
        print(f"Error: {TRAINERS_S} not found.", file=sys.stderr)
        sys.exit(1)

    original = TRAINERS_S.read_text(encoding="utf-8")
    new_text, total, locked, changed = reroll_shinylock(original, rng)

    if total == 0:
        print("No `shinylock` lines found — file unchanged.")
        return

    TRAINERS_S.write_text(new_text, encoding="utf-8")

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"Processed {total} shinylock field(s) in {TRAINERS_S.name}")
    if seed is not None:
        print(f"Seed used: {seed}")
    print(f"  shinylock = 1 : {locked:>4}  ({locked/total*100:.2f}%,  expected ~{total/SHINY_CHANCE:.1f})")
    print(f"  shinylock = 0 : {total - locked:>4}")
    print(f"  Values changed from previous: {changed}")


if __name__ == "__main__":
    main()

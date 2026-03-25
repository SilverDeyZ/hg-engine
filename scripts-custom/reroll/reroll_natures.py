#!/usr/bin/env python3
"""
reroll_natures.py

Replaces every `nature NATURE_XXX` line in armips/data/trainers/trainers.s
with a freshly randomised nature chosen from the 25 natures defined in
armips/include/constants.s.

Usage:
    python3 scripts-custom/reroll/reroll_natures.py [--seed N]

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

# ── Nature list — order mirrors armips/include/constants.s lines 502-526 ──
# NATURE_HARDY=0 … NATURE_QUIRKY=24
NATURES = [
    "NATURE_HARDY",   "NATURE_LONELY",  "NATURE_BRAVE",   "NATURE_ADAMANT", "NATURE_NAUGHTY",
    "NATURE_BOLD",    "NATURE_DOCILE",  "NATURE_RELAXED", "NATURE_IMPISH",  "NATURE_LAX",
    "NATURE_TIMID",   "NATURE_HASTY",   "NATURE_SERIOUS", "NATURE_JOLLY",   "NATURE_NAIVE",
    "NATURE_MODEST",  "NATURE_MILD",    "NATURE_QUIET",   "NATURE_BASHFUL", "NATURE_RASH",
    "NATURE_CALM",    "NATURE_GENTLE",  "NATURE_SASSY",   "NATURE_CAREFUL", "NATURE_QUIRKY",
]

# Matches:  <leading whitespace> nature <NATURE_SYMBOL>
_NATURE_RE = re.compile(r'^(\s*)nature\s+(NATURE_\w+)\s*$')


def reroll_natures(text: str, rng: random.Random) -> tuple[str, int, dict]:
    """
    Replace every `nature NATURE_XXX` line with a random nature.

    Returns:
        new_text    – the transformed file content
        count       – number of lines changed
        tally       – {NATURE_NAME: how_many_times_chosen}
    """
    lines   = text.splitlines(keepends=True)
    changed = 0
    tally: dict[str, int] = {}

    for i, line in enumerate(lines):
        m = _NATURE_RE.match(line)
        if not m:
            continue
        indent   = m.group(1)
        new_nat  = rng.choice(NATURES)
        lines[i] = f"{indent}nature {new_nat}\n"
        tally[new_nat] = tally.get(new_nat, 0) + 1
        changed += 1

    return "".join(lines), changed, tally


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
    new_text, changed, tally = reroll_natures(original, rng)

    if changed == 0:
        print("No `nature` lines found — file unchanged.")
        return

    TRAINERS_S.write_text(new_text, encoding="utf-8")

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"Rerolled {changed} nature(s) in {TRAINERS_S.name}")
    if seed is not None:
        print(f"Seed used: {seed}")
    print("\nNature distribution:")
    for nat in NATURES:
        n = tally.get(nat, 0)
        if n:
            bar = "█" * (n // max(1, changed // 40))
            print(f"  {nat:<20} {n:>4}  {bar}")
    missing = [nat for nat in NATURES if nat not in tally]
    if missing:
        print(f"\n  ({len(missing)} nature(s) not assigned this run: "
              f"{', '.join(missing)})")


if __name__ == "__main__":
    main()

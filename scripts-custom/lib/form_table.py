"""
form_table.py
=============
Parse data/PokeFormDataTbl.c to build the authoritative
form-species → (base_species, form_id) mapping.

Used by trainer_writer.py to decide the correct armips emit syntax:

  Base-range species (index ≤ NUM_OF_MONS = 1075):
    → `pokemon SPECIES_X`          (valid with the pokemon macro)

  Form-range species (index > 1075, defined in PokeFormDataTbl.c):
    → `monwithform BASE_SPECIES, formId`

PokeFormDataTbl.c intentionally covers ONLY form-range species.
Base-range form species (Wormadam Sandy 499, Rotom Heat 503,
Giratina Origin 501, etc.) are absent from the table and continue
to use the `pokemon` macro directly.

form_id is 1-based within each base species family:
  form 0  = base species  (always written as `pokemon`)
  form N  = Nth entry in the PokeFormDataTbl row for that base species
"""

from __future__ import annotations

import re
from pathlib import Path

# ── Regex patterns ────────────────────────────────────────────────────────────

# [SPECIES_X] = {
_RE_BASE_ENTRY = re.compile(r'^\s+\[([A-Z][A-Z_0-9]*)\]\s*=\s*\{')

# (NEEDS_REVERSION | )?SPECIES_Y,
_RE_FORM_ENTRY = re.compile(
    r'^\s+(?:NEEDS_REVERSION\s*\|\s*)?([A-Z][A-Z_0-9]*),?'
)

# },   — closes an inner form list
_RE_END_ENTRY = re.compile(r'^\s+\},')


def build_form_map(path: Path) -> dict[str, tuple[str, int]]:
    """
    Parse PokeFormDataTbl.c and return a mapping:

        { form_species_symbol: (base_species_symbol, form_id) }

    form_id is 1-based.  All preprocessor guards (#ifdef / #endif) are
    skipped — every form family is included regardless of config flag.
    This is safe because the candidate engine already excludes non-assignable
    form types (mega, primal, battle_form, etc.) from the candidate pool.
    """
    form_map: dict[str, tuple[str, int]] = {}
    current_base: str | None = None
    form_id: int = 0

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()

            # Skip blank lines, preprocessor directives, C comments
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            # Detect [SPECIES_X] = {
            m = _RE_BASE_ENTRY.match(line)
            if m:
                current_base = m.group(1)
                form_id = 0
                continue

            # Detect }, — end of inner form list
            if _RE_END_ENTRY.match(line):
                current_base = None
                form_id = 0
                continue

            # Inside a base species block: extract form species
            if current_base is not None:
                m = _RE_FORM_ENTRY.match(line)
                if m:
                    sym = m.group(1)
                    if sym.startswith("SPECIES_"):
                        form_id += 1
                        form_map[sym] = (current_base, form_id)

    return form_map


def build_reverse_form_map(
    form_map: dict[str, tuple[str, int]],
) -> dict[tuple[str, int], str]:
    """
    Build the inverse of form_map:
        {(base_species_symbol, form_id): form_species_symbol}

    Used by trainer_parser to reconstruct the full form species symbol from
    `monwithform BASE, N` lines.  Without this, the parser would only store
    the base species and lose form identity.

    Example:
        form_map = {"SPECIES_GRAVELER_ALOLAN": ("SPECIES_GRAVELER", 1)}
        reverse  = {("SPECIES_GRAVELER", 1): "SPECIES_GRAVELER_ALOLAN"}
    """
    return {(base, fid): sym for sym, (base, fid) in form_map.items()}

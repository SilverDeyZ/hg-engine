"""
learnset_index.py
=================
Indexes data/learnsets/learnsets.json for quick level-up move lookup.

Provides:
  - get_level_moves(species, max_level) → last four moves at or below that level
  - get_all_level_moves(species) → full sorted list of (level, move) pairs

The JSON structure is:
  {
    "SPECIES_X": {
      "LevelMoves": [{"Level": N, "Move": "MOVE_Y"}, ...],
      ...
    }
  }
"""

from __future__ import annotations

import json
import random
from pathlib import Path


def load_learnsets(path: Path) -> dict[str, dict]:
    """Load learnsets.json and return the raw dict."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_level_move_index(
    raw: dict[str, dict],
) -> dict[str, list[tuple[int, str]]]:
    """
    Pre-process all species LevelMoves into sorted (level, move) lists.
    Returns {species_symbol: [(level, move), ...]} sorted ascending by level.
    """
    index: dict[str, list[tuple[int, str]]] = {}
    for species, data in raw.items():
        level_moves = data.get("LevelMoves", [])
        pairs = [(entry["Level"], entry["Move"]) for entry in level_moves]
        pairs.sort(key=lambda x: x[0])
        index[species] = pairs
    return index


def get_moves_at_level(
    level_moves: list[tuple[int, str]],
    max_level: int,
    count: int = 4,
) -> list[str]:
    """
    Return the last `count` moves learned at or below max_level.

    Ties at the boundary cutoff level are broken by taking moves in
    learnset order (deterministic, no RNG).  Use pick_moves_rng() when
    random tie-breaking is required.

    Returns a list of MOVE_ symbols, length == count (padded with MOVE_NONE).
    """
    eligible = [(lvl, mv) for lvl, mv in level_moves if lvl <= max_level]

    if not eligible:
        return ["MOVE_NONE"] * count

    if len(eligible) <= count:
        moves = [mv for _, mv in eligible]
        moves += ["MOVE_NONE"] * (count - len(moves))
        return moves

    # boundary_level = level of the (count)th-from-last eligible move.
    # Moves above this level are always included (after_boundary).
    # Moves at this level may need tie-breaking to fill remaining slots.
    boundary_level   = eligible[-count][0]
    after_boundary   = [mv for lvl, mv in eligible if lvl > boundary_level]
    all_at_boundary  = [mv for lvl, mv in eligible if lvl == boundary_level]
    slots_for_bndry  = count - len(after_boundary)

    if len(all_at_boundary) <= slots_for_bndry:
        result = all_at_boundary + after_boundary
    else:
        # Tie: take first slots_for_bndry in learnset order (deterministic).
        result = all_at_boundary[:slots_for_bndry] + after_boundary

    result += ["MOVE_NONE"] * (count - len(result))
    return result[:count]


def resolve_learnset_symbol(
    species_symbol: str,
    level_move_index: dict[str, list[tuple[int, str]]],
    form_map: dict[str, tuple[str, int]] | None = None,
) -> str | None:
    """
    Resolve a species symbol to a key present in level_move_index.

    Resolution order:

      1. Direct lookup — the species has its own learnset entry.

      2. Form-map lookup — if the species is in form_map (i.e. it is a
         form-range species defined in PokeFormDataTbl.c), look up its base
         species.  This is the authoritative fallback: e.g.
           SPECIES_GRAVELER_ALOLAN  → base = SPECIES_GRAVELER  (form_map)
           SPECIES_YAMASK_GALARIAN  → base = SPECIES_YAMASK    (form_map)
         Prefer this over suffix-stripping because it is grounded in the
         actual form table rather than heuristic string manipulation.

      3. Last-resort suffix stripping — for any remaining cases (e.g. base-range
         form species that are not in form_map because they don't need
         monwithform syntax).  Strip trailing underscore-delimited tokens until
         a match is found or no further stripping is possible.

    Returns the matched symbol string, or None if nothing is found.
    """
    # 1. Direct lookup
    if species_symbol in level_move_index:
        return species_symbol

    # 2. Form-map lookup (authoritative for form-range species)
    if form_map is not None and species_symbol in form_map:
        base_sym, _ = form_map[species_symbol]
        if base_sym in level_move_index:
            return base_sym

    # 3. Last-resort suffix stripping
    sym = species_symbol
    prefix_len = len("SPECIES_")
    while True:
        last_us = sym.rfind("_", prefix_len)
        if last_us == -1:
            return None
        sym = sym[:last_us]
        if sym in level_move_index:
            return sym


def pick_moves_rng(
    level_moves: list[tuple[int, str]],
    max_level: int,
    rng: random.Random,
    count: int = 4,
) -> tuple[list[str], int, bool, bool]:
    """
    RNG-aware move selection for Phase 5.

    Identical logic to get_moves_at_level() but uses random.sample() to
    resolve boundary-level ties instead of taking moves in learnset order.

    Parameters
    ----------
    level_moves : pre-sorted (level, move) list for the species
    max_level   : trainer slot level
    rng         : seeded Random instance (consumed in-place for tied picks)
    count       : number of move slots (always 4)

    Returns
    -------
    (moves, learned_count, used_none, tie_broken)
      moves         : list of MOVE_ symbols, length == count
      learned_count : number of eligible moves at or below max_level
      used_none     : True if any slot is MOVE_NONE
      tie_broken    : True if RNG was needed to resolve a boundary tie
    """
    eligible = [(lvl, mv) for lvl, mv in level_moves if lvl <= max_level]
    learned_count = len(eligible)
    tie_broken    = False

    if not eligible:
        return ["MOVE_NONE"] * count, 0, True, False

    if len(eligible) <= count:
        moves     = [mv for _, mv in eligible]
        moves    += ["MOVE_NONE"] * (count - len(moves))
        used_none = len(eligible) < count
        return moves, learned_count, used_none, False

    # boundary_level = level of the (count)th-from-last eligible move.
    boundary_level  = eligible[-count][0]
    after_boundary  = [mv for lvl, mv in eligible if lvl > boundary_level]
    all_at_boundary = [mv for lvl, mv in eligible if lvl == boundary_level]
    slots_for_bndry = count - len(after_boundary)

    if len(all_at_boundary) <= slots_for_bndry:
        # All boundary-level moves fit — no tie to break
        result = all_at_boundary + after_boundary
    else:
        # Genuine tie: randomly sample without replacement
        chosen = rng.sample(all_at_boundary, slots_for_bndry)
        result  = chosen + after_boundary
        tie_broken = True

    result   += ["MOVE_NONE"] * (count - len(result))
    result    = result[:count]
    used_none = any(m == "MOVE_NONE" for m in result)
    return result, learned_count, used_none, tie_broken

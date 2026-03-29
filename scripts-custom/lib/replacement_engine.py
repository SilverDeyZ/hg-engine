"""
replacement_engine.py
=====================
Phase 4: weighted random selection of a final replacement species for each
trainer party slot.

Selection rules (applied in order):
  1. Candidate pool is already filtered by category rule, type overlap,
     egg-group overlap, and BST tier (supplied from candidate_engine.py).
  2. For mono-type specialists, candidate must contain the specialty type
     (hard filter — if no candidate survives, slot is kept unchanged).
  3. Weighted random choice from the survivors:
       base weight = max(1, BST_TIER_3 − |bst_delta|)   (closer BST → heavier)
       × 1.5 if candidate shares source's primary type (type1)
       × 1.25 if two or more egg groups are shared

If no valid candidate remains after all filters, the slot is flagged
unchanged with a reason string.
"""

from __future__ import annotations

import random
from typing import Optional

from .mondata_index import SpeciesRecord
from .candidate_engine import CandidateMatch, BST_TIER_3


# ── Selection ─────────────────────────────────────────────────────────────────

def select_replacement(
    matches: list[CandidateMatch],
    src: SpeciesRecord,
    symbol_index: dict[str, SpeciesRecord],
    specialty_type: Optional[str],
    rng: random.Random,
) -> tuple[Optional[CandidateMatch], bool, str]:
    """
    Choose a replacement for `src` from `matches`.

    Parameters
    ----------
    matches        : pre-built candidate pool for src (may be empty)
    src            : source SpeciesRecord
    symbol_index   : full species lookup for resolving candidate types
    specialty_type : required type for mono-type specialists, or None
    rng            : seeded Random instance

    Returns
    -------
    (chosen, mono_applied, reason)
      chosen       : CandidateMatch if a replacement was found, else None
      mono_applied : True if the specialty_type filter was applied
      reason       : "ok" on success, otherwise a short diagnostic string
    """
    if not matches:
        return None, False, "no_candidates_in_pool"

    eligible: list[CandidateMatch] = list(matches)
    mono_applied = False

    # ── Mono-type specialist filter ────────────────────────────────────────────
    if specialty_type:
        filtered = [
            m for m in eligible
            if specialty_type in _types(m.candidate_species, symbol_index)
        ]
        if filtered:
            eligible = filtered
            mono_applied = True
        else:
            return None, False, f"no_candidates_for_specialty:{specialty_type}"

    # ── Weighted selection ─────────────────────────────────────────────────────
    weights = [_weight(m, src, symbol_index) for m in eligible]
    chosen = rng.choices(eligible, weights=weights, k=1)[0]
    return chosen, mono_applied, "ok"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _types(symbol: str, symbol_index: dict[str, SpeciesRecord]) -> frozenset[str]:
    rec = symbol_index.get(symbol)
    return rec.types_set() if rec else frozenset()


def _weight(
    m: CandidateMatch,
    src: SpeciesRecord,
    symbol_index: dict[str, SpeciesRecord],
) -> float:
    """Compute selection weight for a CandidateMatch."""
    # Base weight: higher for lower BST delta (max = BST_TIER_3 at delta=0)
    w = float(max(1, BST_TIER_3 - abs(m.bst_delta)))

    # Primary-type bonus: candidate explicitly carries source's type1
    cand_types = _types(m.candidate_species, symbol_index)
    if src.type1 and src.type1 in cand_types:
        w *= 1.5

    # Dual egg-group bonus
    if m.shared_egggroups and len(m.shared_egggroups.split(",")) >= 2:
        w *= 1.25

    return w

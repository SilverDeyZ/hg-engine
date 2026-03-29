"""
candidate_engine.py
===================
Phase 3: build candidate replacement pools for every source species.

For each species that can appear in a trainer party:
  1. Determine its category group (normal / legendary / mythical / ...)
  2. Choose the correct candidate pool:
       - normal source  → normal-pool candidates (excluded categories removed)
       - excluded source → same-category candidates only
  3. Filter by type overlap  (≥1 shared type)
  4. Filter by egg-group overlap (≥1 shared egg group)
  5. Assign fallback tier based on |BST delta|:
       tier 1 = ±45   (preferred)
       tier 2 = ±70
       tier 3 = ±105
       (candidates outside ±105 are discarded)

For mono-type specialists the caller applies an additional filter:
  candidate must contain the specialty type.
  This is done at Phase 4 selection time, not here.

Outputs via write_candidate_csvs():
  candidate_matches.csv     — one row per (source, candidate) within tier 3
  candidate_pool_summary.csv — one row per source species with tier counts
"""

from __future__ import annotations

from dataclasses import dataclass

from .mondata_index import SpeciesRecord

# ── BST tier windows ─────────────────────────────────────────────────────────

BST_TIER_1 = 45
BST_TIER_2 = 70
BST_TIER_3 = 105

# Form types that are valid as *candidates* even if they are excluded from the
# normal pool.  Regional variants and cosmetic forms can still be assigned;
# totem forms are borderline but kept.
_ASSIGNABLE_FORM_TYPES = frozenset({
    "base",
    "regional",
    "cosmetic_form",
})


# ── Data structure ────────────────────────────────────────────────────────────

@dataclass
class CandidateMatch:
    source_species: str
    candidate_species: str
    shared_types: str       # comma-separated sorted type names
    shared_egggroups: str   # comma-separated sorted egg-group names
    bst_delta: int          # candidate.bst − source.bst
    category_rule: str      # "normal_pool" | "same_category:<cat>"
    fallback_tier: int      # 1, 2, or 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bst_tier(bst_delta: int) -> int:
    """Return 1/2/3 for the tier bracket, or 0 if outside tier 3."""
    abs_d = abs(bst_delta)
    if abs_d <= BST_TIER_1:
        return 1
    if abs_d <= BST_TIER_2:
        return 2
    if abs_d <= BST_TIER_3:
        return 3
    return 0


def _is_valid_candidate(record: SpeciesRecord) -> bool:
    """
    True if a species can be assigned as a replacement candidate.
    Megas, gmax, primals, battle-only forms, stubs, and alt-forms cannot.
    """
    return record.form_type in _ASSIGNABLE_FORM_TYPES


# ── Core pool builder ─────────────────────────────────────────────────────────

def build_candidate_pools(
    species_list: list[SpeciesRecord],
) -> dict[str, list[CandidateMatch]]:
    """
    Build a candidate pool for every potential source species.

    Returns {source_symbol: [CandidateMatch, ...]} containing all candidates
    within tier 3.  Sources with an empty list have no viable replacement.

    Coverage:
      - All normal-pool species (excluded_from_normal_pool=False) are treated
        as sources and draw from the full normal pool.
      - All excluded-category species whose form_type is assignable are also
        treated as sources and draw from the same-category pool.
      - Species with non-assignable form_type (mega, alt_form, etc.) are
        skipped as sources — trainers should not normally carry them, and
        if they do, no replacement will be attempted.
    """
    # ── Build candidate sub-pools ─────────────────────────────────────────────

    # Normal pool: all species not excluded AND with an assignable form type.
    normal_candidates: list[SpeciesRecord] = [
        r for r in species_list
        if not r.excluded_from_normal_pool and _is_valid_candidate(r)
    ]

    # Per-category pools for excluded categories.
    # Only species with assignable form types enter as candidates.
    category_candidates: dict[str, list[SpeciesRecord]] = {}
    for r in species_list:
        if r.category_group != "normal" and _is_valid_candidate(r):
            category_candidates.setdefault(r.category_group, []).append(r)

    # ── Iterate over potential source species ─────────────────────────────────

    pools: dict[str, list[CandidateMatch]] = {}

    for src in species_list:

        # Determine candidate pool and category rule label.
        if src.category_group == "normal":
            if not _is_valid_candidate(src):
                # Non-assignable form (mega, alt_form, etc.) — skip as source.
                continue
            cand_pool = normal_candidates
            category_rule = "normal_pool"
        else:
            # Excluded-category source.
            if not _is_valid_candidate(src):
                # Alt-form of a legendary etc. — skip as source.
                continue
            cat = src.category_group
            cand_pool = category_candidates.get(cat, [])
            category_rule = f"same_category:{cat}"

        src_types = src.types_set()
        src_eggs  = src.egggroups_set()
        matches: list[CandidateMatch] = []

        for cand in cand_pool:
            if cand.symbol == src.symbol:
                continue  # no self-replacement

            # ── Type overlap ──────────────────────────────────────────────────
            shared_types = src_types & cand.types_set()
            if not shared_types:
                continue

            # ── Egg-group overlap ─────────────────────────────────────────────
            shared_eggs = src_eggs & cand.egggroups_set()
            if not shared_eggs:
                continue

            # ── BST window ────────────────────────────────────────────────────
            bst_delta = cand.bst - src.bst
            tier = _bst_tier(bst_delta)
            if tier == 0:
                continue

            matches.append(CandidateMatch(
                source_species=src.symbol,
                candidate_species=cand.symbol,
                shared_types=",".join(sorted(shared_types)),
                shared_egggroups=",".join(sorted(shared_eggs)),
                bst_delta=bst_delta,
                category_rule=category_rule,
                fallback_tier=tier,
            ))

        pools[src.symbol] = matches

    return pools


# ── Summary helper ────────────────────────────────────────────────────────────

def pool_summary_rows(
    pools: dict[str, list[CandidateMatch]],
) -> list[dict]:
    """
    Return one summary dict per source species with cumulative tier counts.

    Counts are cumulative: count_tier2 includes tier-1 candidates as well.
    no_candidates=1 flags sources where even tier 3 is empty.
    """
    rows = []
    for source, matches in sorted(pools.items()):
        t1 = sum(1 for m in matches if m.fallback_tier == 1)
        t2 = sum(1 for m in matches if m.fallback_tier <= 2)
        t3 = len(matches)  # all are tier ≤ 3 by construction
        rows.append({
            "source_species":  source,
            "count_tier1":     t1,
            "count_tier2":     t2,
            "count_tier3":     t3,
            "no_candidates":   int(t3 == 0),
        })
    return rows

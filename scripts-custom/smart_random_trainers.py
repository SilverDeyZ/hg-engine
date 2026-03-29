#!/usr/bin/env python3
"""
smart_random_trainers.py
========================
Orchestrator for the smart trainer randomisation pipeline.

Usage:
  python scripts-custom/smart_random_trainers.py index
  python scripts-custom/smart_random_trainers.py candidates
  python scripts-custom/smart_random_trainers.py replace [--seed N]
  python scripts-custom/smart_random_trainers.py moves    [--seed N]
  python scripts-custom/smart_random_trainers.py validate
  python scripts-custom/smart_random_trainers.py write
  python scripts-custom/smart_random_trainers.py all      [--seed N]

Output datasets (written to scripts-custom/datasets/):
  species_index.csv, trainer_party_index.csv, mono_type_trainers.csv
  candidate_matches.csv, candidate_pool_summary.csv
  final_replacements.csv, final_movesets.csv
  validation_report.csv, write_summary.csv

Rewritten file:
  armips/data/trainers/trainers.s   (backup: bak/trainers.s.bak)
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

# ── Path setup ───────────────────────────────────────────────────────────────

REPO_ROOT   = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
DATASETS    = SCRIPTS_DIR / "datasets"

MONDATA_PATH   = REPO_ROOT / "armips" / "data" / "mondata.s"
TRAINERS_PATH  = REPO_ROOT / "armips" / "data" / "trainers" / "trainers.s"
LEARNSETS_PATH = REPO_ROOT / "data" / "learnsets" / "learnsets.json"
FORM_DATA_PATH = REPO_ROOT / "data" / "PokeFormDataTbl.c"

# Add lib to path
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.mondata_index    import parse_mondata, build_symbol_index, SpeciesRecord
from lib.trainer_parser   import parse_trainers, TrainerRecord
from lib.learnset_index   import load_learnsets, build_level_move_index, pick_moves_rng, resolve_learnset_symbol
from lib.species_rules    import MONO_TYPE_BY_CLASS
from lib.candidate_engine import build_candidate_pools, pool_summary_rows, CandidateMatch
from lib.replacement_engine import select_replacement
from lib.validation       import run_all as run_validation, ValidationRow
from lib.trainer_writer   import rewrite_trainers, WriteStats
from lib.form_table       import build_form_map, build_reverse_form_map

DEFAULT_SEED = 42


# ── Phase 0+1: index ─────────────────────────────────────────────────────────

def cmd_index() -> None:
    """Parse all source data and write normalised CSV datasets."""
    DATASETS.mkdir(parents=True, exist_ok=True)

    print("[index] Loading form table …")
    form_map         = build_form_map(FORM_DATA_PATH)
    reverse_form_map = build_reverse_form_map(form_map)
    print(f"  → {len(form_map)} form-range species entries")

    print("[index] Parsing mondata.s …")
    species_list = parse_mondata(MONDATA_PATH)
    symbol_index = build_symbol_index(species_list)
    print(f"  → {len(species_list)} species parsed")

    print("[index] Parsing trainers.s …")
    trainers = parse_trainers(TRAINERS_PATH, reverse_form_map=reverse_form_map)
    print(f"  → {len(trainers)} trainer records parsed")

    print("[index] Loading learnsets.json …")
    learnsets_raw = load_learnsets(LEARNSETS_PATH)
    level_move_index = build_level_move_index(learnsets_raw)
    print(f"  → {len(level_move_index)} species learnsets indexed")

    print("[index] Writing species_index.csv …")
    _write_species_index(species_list)

    print("[index] Writing trainer_party_index.csv …")
    _write_trainer_party_index(trainers)

    print("[index] Writing mono_type_trainers.csv …")
    _write_mono_type_trainers(trainers)

    print("[index] Done.")
    print(f"  Datasets written to: {DATASETS}")


def _write_species_index(species_list: list[SpeciesRecord]) -> None:
    out_path = DATASETS / "species_index.csv"
    fieldnames = [
        "species",
        "display_name",
        "base_form_group",
        "type1",
        "type2",
        "egggroup1",
        "egggroup2",
        "hp",
        "atk",
        "def",
        "spe",
        "spa",
        "spd",
        "bst",
        "form_type",
        "category_group",
        "excluded_from_normal_pool",
        "exclusion_reason",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in species_list:
            writer.writerow({
                "species":                  r.symbol,
                "display_name":             r.display_name,
                "base_form_group":          r.base_form_group,
                "type1":                    r.type1,
                "type2":                    r.type2,
                "egggroup1":                r.egggroup1,
                "egggroup2":                r.egggroup2,
                "hp":                       r.hp,
                "atk":                      r.atk,
                "def":                      r.def_,
                "spe":                      r.spe,
                "spa":                      r.spa,
                "spd":                      r.spd,
                "bst":                      r.bst,
                "form_type":                r.form_type,
                "category_group":           r.category_group,
                "excluded_from_normal_pool":int(r.excluded_from_normal_pool),
                "exclusion_reason":         r.exclusion_reason,
            })


def _write_trainer_party_index(trainers: list[TrainerRecord]) -> None:
    out_path = DATASETS / "trainer_party_index.csv"
    fieldnames = [
        "trainer_id",
        "trainer_name",
        "trainer_class",
        "battle_type",
        "party_slot",
        "original_species",
        "level",
        "move1",
        "move2",
        "move3",
        "move4",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for t in trainers:
            if not t.party:
                # Trainer with no party: write a placeholder row for completeness
                writer.writerow({
                    "trainer_id":      t.trainer_id,
                    "trainer_name":    t.trainer_name,
                    "trainer_class":   t.trainer_class,
                    "battle_type":     t.battle_type,
                    "party_slot":      "",
                    "original_species":"",
                    "level":           "",
                    "move1":           "",
                    "move2":           "",
                    "move3":           "",
                    "move4":           "",
                })
                continue
            for slot in t.party:
                writer.writerow({
                    "trainer_id":      t.trainer_id,
                    "trainer_name":    t.trainer_name,
                    "trainer_class":   t.trainer_class,
                    "battle_type":     t.battle_type,
                    "party_slot":      slot.slot_index,
                    "original_species":slot.species,
                    "level":           slot.level,
                    "move1":           slot.move(0),
                    "move2":           slot.move(1),
                    "move3":           slot.move(2),
                    "move4":           slot.move(3),
                })


def _write_mono_type_trainers(trainers: list[TrainerRecord]) -> None:
    """
    Detect mono-type specialists using the class override table.
    confidence = "class_table" for class-based detection.

    Heuristic detection (party composition analysis) is NOT done here;
    the class table is the authoritative source per spec.
    """
    out_path = DATASETS / "mono_type_trainers.csv"
    fieldnames = [
        "trainer_id",
        "trainer_name",
        "trainer_class",
        "specialty_type",
        "confidence",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for t in trainers:
            spec_type = MONO_TYPE_BY_CLASS.get(t.trainer_class)
            if spec_type:
                writer.writerow({
                    "trainer_id":    t.trainer_id,
                    "trainer_name":  t.trainer_name,
                    "trainer_class": t.trainer_class,
                    "specialty_type":spec_type,
                    "confidence":    "class_table",
                })


# ── Stub phases ───────────────────────────────────────────────────────────────

def cmd_candidates() -> None:
    """Phase 3: build candidate pools and write candidate CSVs."""
    DATASETS.mkdir(parents=True, exist_ok=True)

    print("[candidates] Parsing mondata.s …")
    species_list = parse_mondata(MONDATA_PATH)
    print(f"  → {len(species_list)} species loaded")

    print("[candidates] Building candidate pools …")
    pools = build_candidate_pools(species_list)

    total_sources    = len(pools)
    no_cand_sources  = sum(1 for m in pools.values() if not m)
    total_pairs      = sum(len(m) for m in pools.values())
    print(f"  → {total_sources} source species processed")
    print(f"  → {total_pairs} total candidate pairs within tier-3 window")
    if no_cand_sources:
        print(f"  ⚠  {no_cand_sources} source(s) have NO candidates even at ±105 BST")

    print("[candidates] Writing candidate_matches.csv …")
    _write_candidate_matches(pools)

    print("[candidates] Writing candidate_pool_summary.csv …")
    _write_candidate_pool_summary(pools)

    # Report zero-candidate sources for visibility
    if no_cand_sources:
        print("[candidates] Zero-candidate sources:")
        for sym, matches in sorted(pools.items()):
            if not matches:
                print(f"    {sym}")

    print("[candidates] Done.")
    print(f"  Datasets written to: {DATASETS}")


def _write_candidate_matches(pools: dict[str, list[CandidateMatch]]) -> None:
    out_path = DATASETS / "candidate_matches.csv"
    fieldnames = [
        "original_species",
        "candidate_species",
        "shared_types",
        "shared_egggroups",
        "bst_delta",
        "category_rule",
        "fallback_tier",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for source, matches in sorted(pools.items()):
            for m in sorted(matches, key=lambda x: (x.fallback_tier, abs(x.bst_delta))):
                writer.writerow({
                    "original_species":  m.source_species,
                    "candidate_species": m.candidate_species,
                    "shared_types":      m.shared_types,
                    "shared_egggroups":  m.shared_egggroups,
                    "bst_delta":         m.bst_delta,
                    "category_rule":     m.category_rule,
                    "fallback_tier":     m.fallback_tier,
                })


def _write_candidate_pool_summary(pools: dict[str, list[CandidateMatch]]) -> None:
    out_path = DATASETS / "candidate_pool_summary.csv"
    fieldnames = [
        "source_species",
        "count_tier1",
        "count_tier2",
        "count_tier3",
        "no_candidates",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in pool_summary_rows(pools):
            writer.writerow(row)


def cmd_replace(seed: int = DEFAULT_SEED) -> None:
    """Phase 4: weighted random replacement selection per trainer party slot."""
    DATASETS.mkdir(parents=True, exist_ok=True)

    print(f"[replace] RNG seed: {seed}")

    print("[replace] Loading form table …")
    form_map         = build_form_map(FORM_DATA_PATH)
    reverse_form_map = build_reverse_form_map(form_map)
    print(f"  → {len(form_map)} form-range species entries")

    print("[replace] Parsing mondata.s …")
    species_list = parse_mondata(MONDATA_PATH)
    symbol_index = build_symbol_index(species_list)
    print(f"  → {len(species_list)} species loaded")

    print("[replace] Building candidate pools …")
    pools = build_candidate_pools(species_list)
    print(f"  → {len(pools)} source species have pools")

    print("[replace] Parsing trainers.s …")
    trainers = parse_trainers(TRAINERS_PATH, reverse_form_map=reverse_form_map)
    print(f"  → {len(trainers)} trainers loaded")

    rng = random.Random(seed)

    print("[replace] Selecting replacements …")
    rows: list[dict] = []
    for t in trainers:
        specialty_type = MONO_TYPE_BY_CLASS.get(t.trainer_class)
        for slot in t.party:
            src_sym = slot.species
            src     = symbol_index.get(src_sym)
            matches = pools.get(src_sym)

            if src is None or matches is None:
                # Non-assignable form or unknown symbol — never in pools
                rows.append(_make_unchanged_row(t, slot, "source_not_in_pool"))
                continue

            chosen, mono_applied, reason = select_replacement(
                matches, src, symbol_index, specialty_type, rng
            )

            if chosen is None:
                rows.append(_make_unchanged_row(t, slot, reason))
            else:
                rows.append({
                    "trainer_id":              t.trainer_id,
                    "trainer_name":            t.trainer_name,
                    "trainer_class":           t.trainer_class,
                    "slot":                    slot.slot_index,
                    "original_species":        src_sym,
                    "new_species":             chosen.candidate_species,
                    "bst_delta":               chosen.bst_delta,
                    "shared_types":            chosen.shared_types,
                    "shared_egggroups":        chosen.shared_egggroups,
                    "category_rule":           chosen.category_rule,
                    "mono_type_rule_applied":  int(mono_applied),
                    "fallback_tier":           chosen.fallback_tier,
                    "unchanged":               0,
                    "reason":                  reason,
                })

    n_total     = len(rows)
    n_unchanged = sum(1 for r in rows if r["unchanged"])
    n_mono      = sum(1 for r in rows if r.get("mono_type_rule_applied"))
    n_t1        = sum(1 for r in rows if not r["unchanged"] and r["fallback_tier"] == 1)
    n_t2        = sum(1 for r in rows if not r["unchanged"] and r["fallback_tier"] == 2)
    n_t3        = sum(1 for r in rows if not r["unchanged"] and r["fallback_tier"] == 3)

    print(f"  → {n_total} party slots processed")
    print(f"  → {n_total - n_unchanged} replaced  "
          f"(tier1={n_t1}, tier2={n_t2}, tier3={n_t3})")
    print(f"  → {n_unchanged} unchanged (no valid candidate)")
    print(f"  → {n_mono} slots had mono-type specialist rule applied")

    print("[replace] Writing final_replacements.csv …")
    _write_final_replacements(rows)

    print("[replace] Done.")
    print(f"  Datasets written to: {DATASETS}")
    print(f"  Seed used: {seed}")


def _make_unchanged_row(t: TrainerRecord, slot, reason: str) -> dict:
    return {
        "trainer_id":              t.trainer_id,
        "trainer_name":            t.trainer_name,
        "trainer_class":           t.trainer_class,
        "slot":                    slot.slot_index,
        "original_species":        slot.species,
        "new_species":             slot.species,
        "bst_delta":               0,
        "shared_types":            "",
        "shared_egggroups":        "",
        "category_rule":           "",
        "mono_type_rule_applied":  0,
        "fallback_tier":           0,
        "unchanged":               1,
        "reason":                  reason,
    }


def _write_final_replacements(rows: list[dict]) -> None:
    out_path = DATASETS / "final_replacements.csv"
    fieldnames = [
        "trainer_id",
        "trainer_name",
        "trainer_class",
        "slot",
        "original_species",
        "new_species",
        "bst_delta",
        "shared_types",
        "shared_egggroups",
        "category_rule",
        "mono_type_rule_applied",
        "fallback_tier",
        "unchanged",
        "reason",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def cmd_moves(seed: int = DEFAULT_SEED) -> None:
    """Phase 5: reroll moves from learnsets for every final replacement slot."""
    DATASETS.mkdir(parents=True, exist_ok=True)

    print(f"[moves] RNG seed: {seed}")

    # ── Load form table ───────────────────────────────────────────────────────
    print("[moves] Loading form table …")
    form_map         = build_form_map(FORM_DATA_PATH)
    reverse_form_map = build_reverse_form_map(form_map)
    print(f"  → {len(form_map)} form-range species entries")

    # ── Load final replacements ───────────────────────────────────────────────
    replacements_path = DATASETS / "final_replacements.csv"
    if not replacements_path.exists():
        print("[moves] ERROR: final_replacements.csv not found — run 'replace' first.")
        sys.exit(1)

    print("[moves] Loading final_replacements.csv …")
    with open(replacements_path, encoding="utf-8", newline="") as fh:
        repl_rows = list(csv.DictReader(fh))
    print(f"  → {len(repl_rows)} replacement rows loaded")

    # ── Build level lookup from trainers.s ────────────────────────────────────
    print("[moves] Parsing trainers.s for slot levels …")
    trainers = parse_trainers(TRAINERS_PATH, reverse_form_map=reverse_form_map)
    level_lookup: dict[tuple[int, int], int] = {}
    for t in trainers:
        for slot in t.party:
            level_lookup[(t.trainer_id, slot.slot_index)] = slot.level
    print(f"  → {len(level_lookup)} (trainer_id, slot) → level entries")

    # ── Load learnsets ────────────────────────────────────────────────────────
    print("[moves] Loading learnsets.json …")
    learnsets_raw    = load_learnsets(LEARNSETS_PATH)
    level_move_index = build_level_move_index(learnsets_raw)
    print(f"  → {len(level_move_index)} species learnsets indexed")

    # ── Reroll moves per slot ─────────────────────────────────────────────────
    print("[moves] Rerolling moves …")
    rng = random.Random(seed)
    out_rows: list[dict] = []
    n_none      = 0
    n_tied      = 0
    n_no_learn  = 0

    for row in repl_rows:
        trainer_id = int(row["trainer_id"])
        slot_idx   = int(row["slot"])
        species    = row["new_species"]      # final species (may equal original if unchanged)
        level      = level_lookup.get((trainer_id, slot_idx), 0)

        resolved    = resolve_learnset_symbol(species, level_move_index, form_map)
        level_moves = level_move_index[resolved] if resolved else []
        if not resolved:
            n_no_learn += 1

        moves, learned_count, used_none, tie_broken = pick_moves_rng(
            level_moves, level, rng
        )

        if used_none:
            n_none  += 1
        if tie_broken:
            n_tied  += 1

        out_rows.append({
            "trainer_id":       trainer_id,
            "trainer_name":     row["trainer_name"],
            "trainer_class":    row["trainer_class"],
            "slot":             slot_idx,
            "species":          species,
            "level":            level,
            "move1":            moves[0],
            "move2":            moves[1],
            "move3":            moves[2],
            "move4":            moves[3],
            "learned_move_count": learned_count,
            "used_move_none":   int(used_none),
            "tie_broken":       int(tie_broken),
            "seed":             seed,
        })

    print(f"  → {len(out_rows)} slots processed")
    print(f"  → {n_none} slots used MOVE_NONE (fewer than 4 learned moves at level)")
    print(f"  → {n_tied} slots had tie-breaking via RNG")
    if n_no_learn:
        print(f"  ⚠  {n_no_learn} species had no learnset entry — all MOVE_NONE")

    print("[moves] Writing final_movesets.csv …")
    _write_final_movesets(out_rows)

    print("[moves] Done.")
    print(f"  Datasets written to: {DATASETS}")
    print(f"  Seed used: {seed}")


def _write_final_movesets(rows: list[dict]) -> None:
    out_path = DATASETS / "final_movesets.csv"
    fieldnames = [
        "trainer_id",
        "trainer_name",
        "trainer_class",
        "slot",
        "species",
        "level",
        "move1",
        "move2",
        "move3",
        "move4",
        "learned_move_count",
        "used_move_none",
        "tie_broken",
        "seed",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def cmd_validate() -> None:
    """Phase 7: validate all pipeline datasets and write validation_report.csv."""
    DATASETS.mkdir(parents=True, exist_ok=True)

    required = [
        DATASETS / "trainer_party_index.csv",
        DATASETS / "final_replacements.csv",
        DATASETS / "final_movesets.csv",
    ]
    missing = [p for p in required if not p.exists()]
    if missing:
        for p in missing:
            print(f"[validate] ERROR: missing dataset: {p.name} — run earlier phases first.")
        sys.exit(1)

    print("[validate] Running validation checks …")
    results = run_validation(DATASETS, MONDATA_PATH, LEARNSETS_PATH)

    # Tally by status
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    # Print summary per check_id
    check_ids = sorted(set(r.check_id for r in results))
    for cid in check_ids:
        rows = [r for r in results if r.check_id == cid]
        worst = "PASS"
        for r in rows:
            if r.status == "FAIL":
                worst = "FAIL"
            elif r.status == "WARN" and worst == "PASS":
                worst = "WARN"
            elif r.status == "INFO" and worst == "PASS":
                worst = "INFO"
        summary_row = next((r for r in rows if r.trainer_id == "*"), rows[0])
        print(f"  [{worst:4s}] {cid}: {summary_row.issue}")

    # Print per-slot failures
    failures = [r for r in results if r.status == "FAIL"]
    if failures:
        print(f"\n[validate] {len(failures)} FAIL(s):")
        for r in failures:
            print(f"  {r.check_id} trainer={r.trainer_id} slot={r.slot} "
                  f"species={r.species}: {r.issue}")

    print(f"\n[validate] Status counts: " +
          " ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    print("[validate] Writing validation_report.csv …")
    _write_validation_report(results)

    if not failures:
        print("[validate] ✓ All checks passed — pipeline is ready for the write phase.")
    else:
        print(f"[validate] ✗ {len(failures)} check(s) failed — resolve before rewriting trainers.s.")

    # ── Backup plan reminder ──────────────────────────────────────────────────
    bak_dir = REPO_ROOT / "bak"
    print(f"\n[validate] Backup target: {bak_dir / 'trainers.s.bak'}")
    if bak_dir.exists():
        print(f"  bak/ directory exists.")
    else:
        print(f"  bak/ directory does not exist yet — will be created by the write phase.")


def _write_validation_report(results: list[ValidationRow]) -> None:
    out_path = DATASETS / "validation_report.csv"
    fieldnames = ["check_id", "trainer_id", "slot", "status", "species", "issue"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "check_id":   r.check_id,
                "trainer_id": r.trainer_id,
                "slot":       r.slot,
                "status":     r.status,
                "species":    r.species,
                "issue":      r.issue,
            })


def cmd_write() -> None:
    """Phase 6: rewrite trainers.s using final_replacements.csv and final_movesets.csv."""
    required = [
        DATASETS / "final_replacements.csv",
        DATASETS / "final_movesets.csv",
        DATASETS / "validation_report.csv",
    ]
    missing = [p for p in required if not p.exists()]
    if missing:
        for p in missing:
            print(f"[write] ERROR: missing: {p.name} — run earlier phases + validate first.")
        sys.exit(1)

    # ── Load replacements ─────────────────────────────────────────────────────
    print("[write] Loading final_replacements.csv …")
    with open(DATASETS / "final_replacements.csv", encoding="utf-8", newline="") as fh:
        repl_rows = list(csv.DictReader(fh))

    new_species_map:  dict[tuple[int,int], str]       = {}
    is_unchanged:     dict[tuple[int,int], bool]      = {}
    trainer_name_map: dict[int, str]                  = {}
    for r in repl_rows:
        tid  = int(r["trainer_id"])
        slot = int(r["slot"])
        key  = (tid, slot)
        new_species_map[key]  = r["new_species"]
        is_unchanged[key]     = (r["unchanged"] == "1")
        trainer_name_map[tid] = r["trainer_name"]

    # ── Load movesets ─────────────────────────────────────────────────────────
    print("[write] Loading final_movesets.csv …")
    with open(DATASETS / "final_movesets.csv", encoding="utf-8", newline="") as fh:
        move_rows = list(csv.DictReader(fh))

    new_moves_map: dict[tuple[int,int], list[str]] = {}
    for r in move_rows:
        tid  = int(r["trainer_id"])
        slot = int(r["slot"])
        new_moves_map[(tid, slot)] = [r["move1"], r["move2"], r["move3"], r["move4"]]

    # ── Load form map ─────────────────────────────────────────────────────────
    print("[write] Loading form table …")
    form_map         = build_form_map(FORM_DATA_PATH)
    reverse_form_map = build_reverse_form_map(form_map)
    print(f"  → {len(form_map)} form-range species entries loaded")

    # ── Rewrite ───────────────────────────────────────────────────────────────
    bak_path = REPO_ROOT / "bak" / "trainers.s.bak"
    print(f"[write] Creating backup → {bak_path} …")

    print(f"[write] Rewriting {TRAINERS_PATH.name} …")
    stats = rewrite_trainers(
        src=TRAINERS_PATH,
        dst=TRAINERS_PATH,      # in-place; backup is made first inside the writer
        bak=bak_path,
        new_species_map=new_species_map,
        is_unchanged=is_unchanged,
        new_moves_map=new_moves_map,
        trainer_name_map=trainer_name_map,
        form_map=form_map,
    )

    print(f"[write] Done.")
    print(f"  Backup:           {bak_path}")
    print(f"  Species changed:  {stats.species_changed}")
    print(f"  Species kept:     {stats.species_kept}")
    print(f"  Movesets changed: {stats.movesets_changed}")
    print(f"  Total slots:      {stats.total_slots}")

    print("[write] Writing write_summary.csv …")
    _write_summary(stats.summary_rows)

    # ── Post-write parse verification ─────────────────────────────────────────
    print("[write] Post-write parse verification …")
    trainers_after = parse_trainers(TRAINERS_PATH, reverse_form_map=reverse_form_map)
    slots_after = sum(len(t.party) for t in trainers_after)
    print(f"  Trainers parsed:  {len(trainers_after)}")
    print(f"  Party slots:      {slots_after}")
    if slots_after == len(repl_rows):
        print(f"  ✓ Slot count matches replacement table ({slots_after})")
    else:
        print(f"  ✗ Slot count mismatch: expected {len(repl_rows)}, got {slots_after}")

    _spot_check_write(trainers_after, repl_rows, move_rows)


def _write_summary(rows: list[dict]) -> None:
    out_path = DATASETS / "write_summary.csv"
    fieldnames = ["trainer_id", "trainer_name", "slot",
                  "species_changed", "unchanged_flag", "moves_changed"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _spot_check_write(trainers, repl_rows, move_rows) -> None:
    """Spot-check the rewritten file against expectations."""
    import sys as _sys

    # Build lookup maps
    repl_by_key  = {(int(r["trainer_id"]), int(r["slot"])): r for r in repl_rows}
    moves_by_key = {(int(r["trainer_id"]), int(r["slot"])): r for r in move_rows}
    trainer_by_id = {t.trainer_id: t for t in trainers}

    checks = [
        # (label, trainer_id, slot_index)
        ("normal trainer",          1, 0),   # Silver slot 0 (SPECIES_SANDYGAST)
        ("gym leader (Morty)",    246, 0),   # Morty slot 0 (Ghost specialist)
        ("elite four (Karen)",    246, 0),   # will try to find Karen separately
    ]

    # Find Morty and Karen by trainer_class
    for t in trainers:
        if "MORTY" in t.trainer_class and t.party:
            checks.append(("gym leader Morty", t.trainer_id, t.party[0].slot_index))
            break
    for t in trainers:
        if "KAREN" in t.trainer_class and t.party:
            checks.append(("elite four Karen", t.trainer_id, t.party[0].slot_index))
            break
    # Find an unchanged slot
    for r in repl_rows:
        if r["unchanged"] == "1":
            checks.append(("unchanged slot", int(r["trainer_id"]), int(r["slot"])))
            break
    # Find a Fairy-fix species (Marill)
    for r in repl_rows:
        if r["original_species"] == "SPECIES_MARILL":
            checks.append(("Fairy-fix (Marill)", int(r["trainer_id"]), int(r["slot"])))
            break

    print("\n[write] Spot-checks:")
    ok = True
    seen = set()
    for label, tid, slot in checks:
        key = (tid, slot)
        if key in seen:
            continue
        seen.add(key)

        expected_repl = repl_by_key.get(key)
        expected_mv   = moves_by_key.get(key)
        t = trainer_by_id.get(tid)
        if not t or not expected_repl:
            continue

        actual_slot = next((s for s in t.party if s.slot_index == slot), None)
        if actual_slot is None:
            continue

        exp_species = expected_repl["new_species"]
        act_species = actual_slot.species
        unchanged   = expected_repl["unchanged"] == "1"
        species_ok  = (act_species == exp_species)

        exp_moves = [expected_mv[f"move{i}"] for i in range(1, 5)] if expected_mv else []
        act_moves = [actual_slot.move(i) for i in range(4)]
        moves_ok  = (act_moves == exp_moves) if exp_moves else True

        status = "✓" if (species_ok and moves_ok) else "✗"
        flag   = " [unchanged]" if unchanged else ""
        print(f"  {status} {label}{flag}: tid={tid} slot={slot}")
        print(f"      species: expected={exp_species}  actual={act_species}  {'OK' if species_ok else 'MISMATCH'}")
        if exp_moves:
            print(f"      moves:   expected={exp_moves}")
            print(f"               actual  ={act_moves}  {'OK' if moves_ok else 'MISMATCH'}")
        if not (species_ok and moves_ok):
            ok = False

    if ok:
        print("\n[write] ✓ All spot-checks passed.")
    else:
        print("\n[write] ✗ Some spot-checks failed — inspect write_summary.csv.")


def cmd_all(seed: int = DEFAULT_SEED) -> None:
    cmd_index()
    cmd_candidates()
    cmd_replace(seed=seed)
    cmd_moves(seed=seed)
    cmd_validate()
    cmd_write()


# ── Entry point ───────────────────────────────────────────────────────────────

_COMMANDS = {
    "index":      cmd_index,
    "candidates": cmd_candidates,
    "replace":    cmd_replace,
    "moves":      cmd_moves,
    "validate":   cmd_validate,
    "write":      cmd_write,
    "all":        cmd_all,
}


def _parse_seed(args: list[str]) -> int:
    """Extract --seed N from extra argv, return DEFAULT_SEED if absent."""
    for i, arg in enumerate(args):
        if arg == "--seed" and i + 1 < len(args):
            try:
                return int(args[i + 1])
            except ValueError:
                pass
    return DEFAULT_SEED


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        print(f"Usage: python {Path(__file__).name} <command> [--seed N]")
        print(f"Commands: {', '.join(_COMMANDS)}")
        sys.exit(1)
    cmd   = sys.argv[1]
    extra = sys.argv[2:]
    if cmd in ("replace", "moves", "all"):
        seed = _parse_seed(extra)
        _COMMANDS[cmd](seed=seed)
    else:
        _COMMANDS[cmd]()


if __name__ == "__main__":
    main()

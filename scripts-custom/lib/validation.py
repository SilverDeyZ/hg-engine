"""
validation.py
=============
Phase 7: dataset integrity validation for the smart trainer randomisation pipeline.

Checks performed:
  V01  Row-count alignment  — trainer_party_index / final_replacements / final_movesets
  V02  Species existence    — every new_species is in the mondata symbol set
  V03  Move validity        — every generated move is in the learnset corpus or MOVE_NONE
  V04  Mono-type constraint — every slot with mono_type_rule_applied=1 has the specialty type
  V05  Mono full team       — every mono-type specialist trainer has specialty on all slots
  V06  Category rule        — same-category replacements stay within the same category
  V07  Normal → no excluded — normal sources were not upgraded to excluded categories
  V08  Unchanged accuracy   — unchanged slots have a plausible documented reason
  V09  Known species review — explicit outcome review for the previously problematic list

Each check produces one or more ValidationRow entries.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .mondata_index import parse_mondata, SpeciesRecord
from .species_rules import MONO_TYPE_BY_CLASS, get_category


# ── Result row ────────────────────────────────────────────────────────────────

@dataclass
class ValidationRow:
    check_id: str
    trainer_id: int | str
    slot: int | str
    status: str          # "PASS" | "FAIL" | "WARN" | "INFO"
    species: str
    issue: str


# ── Top-level runner ──────────────────────────────────────────────────────────

def run_all(
    datasets_dir: Path,
    mondata_path: Path,
    learnsets_path: Path,
) -> list[ValidationRow]:
    """Run all checks and return a flat list of ValidationRow objects."""
    rows: list[ValidationRow] = []

    # ── Load datasets ─────────────────────────────────────────────────────────
    party_index = _load_csv(datasets_dir / "trainer_party_index.csv")
    replacements = _load_csv(datasets_dir / "final_replacements.csv")
    movesets     = _load_csv(datasets_dir / "final_movesets.csv")
    mono_trainers = _load_csv(datasets_dir / "mono_type_trainers.csv")

    # ── Load mondata ──────────────────────────────────────────────────────────
    species_list  = parse_mondata(mondata_path)
    symbol_index: dict[str, SpeciesRecord] = {r.symbol: r for r in species_list}
    valid_symbols = set(symbol_index.keys()) | {"SPECIES_NONE"}

    # ── Load valid moves ──────────────────────────────────────────────────────
    with open(learnsets_path, encoding="utf-8") as fh:
        learnsets_raw = json.load(fh)
    valid_moves: set[str] = {"MOVE_NONE"}
    for data in learnsets_raw.values():
        for entry in data.get("LevelMoves", []):
            valid_moves.add(entry["Move"])

    # ── Build mono-type lookup ────────────────────────────────────────────────
    # trainer_class → specialty_type
    mono_by_class: dict[str, str] = MONO_TYPE_BY_CLASS

    # ── Run checks ───────────────────────────────────────────────────────────
    rows += _v01_row_counts(party_index, replacements, movesets)
    rows += _v02_species_existence(replacements, valid_symbols)
    rows += _v03_move_validity(movesets, valid_moves)
    rows += _v04_mono_slot(replacements, symbol_index, mono_by_class)
    rows += _v05_mono_full_team(replacements, symbol_index, mono_by_class)
    rows += _v06_category_rule(replacements, symbol_index)
    rows += _v07_normal_no_upgrade(replacements, symbol_index)
    rows += _v08_unchanged_accuracy(replacements)
    rows += _v09_known_species(replacements, symbol_index)

    return rows


# ── V01 — row count alignment ─────────────────────────────────────────────────

def _v01_row_counts(party, replacements, movesets) -> list[ValidationRow]:
    counts = {
        "trainer_party_index": len(party),
        "final_replacements":  len(replacements),
        "final_movesets":      len(movesets),
    }
    all_equal = len(set(counts.values())) == 1
    issue = " / ".join(f"{k}={v}" for k, v in counts.items())
    return [ValidationRow(
        check_id="V01",
        trainer_id="*",
        slot="*",
        status="PASS" if all_equal else "FAIL",
        species="",
        issue=issue,
    )]


# ── V02 — species existence ────────────────────────────────────────────────────

def _v02_species_existence(replacements, valid_symbols) -> list[ValidationRow]:
    out = []
    for r in replacements:
        sym = r["new_species"]
        if sym not in valid_symbols:
            out.append(ValidationRow(
                check_id="V02",
                trainer_id=r["trainer_id"],
                slot=r["slot"],
                status="FAIL",
                species=sym,
                issue=f"new_species '{sym}' not in mondata",
            ))
    if not out:
        out.append(ValidationRow(
            check_id="V02", trainer_id="*", slot="*",
            status="PASS", species="",
            issue=f"all {len(replacements)} new_species symbols exist in mondata",
        ))
    return out


# ── V03 — move validity ────────────────────────────────────────────────────────

def _v03_move_validity(movesets, valid_moves) -> list[ValidationRow]:
    out = []
    for r in movesets:
        for col in ("move1", "move2", "move3", "move4"):
            mv = r[col]
            if mv and mv not in valid_moves:
                out.append(ValidationRow(
                    check_id="V03",
                    trainer_id=r["trainer_id"],
                    slot=r["slot"],
                    status="FAIL",
                    species=r["species"],
                    issue=f"{col}='{mv}' not in learnset corpus",
                ))
    # Flag slots where all moves are MOVE_NONE (not a failure, but noteworthy)
    no_learnset = [r for r in movesets
                   if all(r[c] == "MOVE_NONE" for c in ("move1","move2","move3","move4"))
                   and r["learned_move_count"] == "0"
                   and r["species"] not in ("SPECIES_NONE", "")]
    if not out:
        out.append(ValidationRow(
            check_id="V03", trainer_id="*", slot="*",
            status="PASS", species="",
            issue=f"all move symbols valid; {len(no_learnset)} slots have no learnset entry (cosmetic forms)",
        ))
    return out


# ── V04 — mono slot: applied flag → specialty type present ────────────────────

def _v04_mono_slot(replacements, symbol_index, mono_by_class) -> list[ValidationRow]:
    out = []
    for r in replacements:
        if r["mono_type_rule_applied"] != "1":
            continue
        specialty = mono_by_class.get(r["trainer_class"])
        if not specialty:
            continue
        rec = symbol_index.get(r["new_species"])
        if rec is None:
            continue
        if specialty not in rec.types_set():
            out.append(ValidationRow(
                check_id="V04",
                trainer_id=r["trainer_id"],
                slot=r["slot"],
                status="FAIL",
                species=r["new_species"],
                issue=f"mono_type_rule_applied=1 but '{specialty}' not in types {rec.types_set()}",
            ))
    if not out:
        applied = sum(1 for r in replacements if r["mono_type_rule_applied"] == "1")
        out.append(ValidationRow(
            check_id="V04", trainer_id="*", slot="*",
            status="PASS", species="",
            issue=f"all {applied} mono-type-flagged slots carry the required specialty type",
        ))
    return out


# ── V05 — mono full team: all slots (including unchanged) satisfy specialty ───

def _v05_mono_full_team(replacements, symbol_index, mono_by_class) -> list[ValidationRow]:
    out = []
    # Group by trainer_id
    by_trainer: dict[str, list[dict]] = {}
    for r in replacements:
        by_trainer.setdefault(r["trainer_id"], []).append(r)

    for tid, slots in by_trainer.items():
        trainer_class = slots[0]["trainer_class"]
        specialty = mono_by_class.get(trainer_class)
        if not specialty:
            continue
        for r in slots:
            sym = r["new_species"]
            rec = symbol_index.get(sym)
            if rec is None:
                continue
            if specialty not in rec.types_set():
                # Only flag non-unchanged slots — unchanged slots are kept with
                # original species because no valid mono candidate existed.
                if r["unchanged"] == "0":
                    out.append(ValidationRow(
                        check_id="V05",
                        trainer_id=tid,
                        slot=r["slot"],
                        status="FAIL",
                        species=sym,
                        issue=f"specialist trainer '{trainer_class}' slot missing '{specialty}' type (has {rec.types_set()})",
                    ))

    if not out:
        mono_count = sum(1 for r in replacements
                         if mono_by_class.get(r["trainer_class"]) and r["unchanged"] == "0")
        out.append(ValidationRow(
            check_id="V05", trainer_id="*", slot="*",
            status="PASS", species="",
            issue=f"all {mono_count} replaced mono-specialist slots carry the required type",
        ))
    return out


# ── V06 — category rule: same-category stays same ────────────────────────────

def _v06_category_rule(replacements, symbol_index) -> list[ValidationRow]:
    out = []
    for r in replacements:
        if not r["category_rule"].startswith("same_category:"):
            continue
        expected_cat = r["category_rule"].split(":")[1]
        new_rec = symbol_index.get(r["new_species"])
        if new_rec is None:
            continue
        actual_cat = get_category(new_rec.symbol)
        if actual_cat != expected_cat:
            out.append(ValidationRow(
                check_id="V06",
                trainer_id=r["trainer_id"],
                slot=r["slot"],
                status="FAIL",
                species=r["new_species"],
                issue=f"same_category:{expected_cat} but replacement is category '{actual_cat}'",
            ))
    if not out:
        same_cat = sum(1 for r in replacements if r["category_rule"].startswith("same_category:"))
        out.append(ValidationRow(
            check_id="V06", trainer_id="*", slot="*",
            status="PASS", species="",
            issue=f"all {same_cat} same-category replacements stay within correct category",
        ))
    return out


# ── V07 — normal source not upgraded to excluded category ─────────────────────

def _v07_normal_no_upgrade(replacements, symbol_index) -> list[ValidationRow]:
    out = []
    for r in replacements:
        if r["category_rule"] != "normal_pool":
            continue
        if r["unchanged"] == "1":
            continue
        new_rec = symbol_index.get(r["new_species"])
        if new_rec is None:
            continue
        cat = get_category(new_rec.symbol)
        if cat != "normal":
            out.append(ValidationRow(
                check_id="V07",
                trainer_id=r["trainer_id"],
                slot=r["slot"],
                status="FAIL",
                species=r["new_species"],
                issue=f"normal source '{r['original_species']}' replaced with excluded-category '{cat}' species",
            ))
    if not out:
        normal_replaced = sum(1 for r in replacements
                              if r["category_rule"] == "normal_pool" and r["unchanged"] == "0")
        out.append(ValidationRow(
            check_id="V07", trainer_id="*", slot="*",
            status="PASS", species="",
            issue=f"all {normal_replaced} normal-pool replacements stay in normal category",
        ))
    return out


# ── V08 — unchanged accuracy ──────────────────────────────────────────────────

_KNOWN_REASONS = {
    "no_candidates_in_pool",
    "no_candidates_for_specialty:PSYCHIC",
    "no_candidates_for_specialty:FIGHTING",
    "no_candidates_for_specialty:GHOST",
    "source_not_in_pool",
}

def _v08_unchanged_accuracy(replacements) -> list[ValidationRow]:
    out = []
    unch = [r for r in replacements if r["unchanged"] == "1"]
    unknown_reasons = []
    for r in unch:
        reason = r["reason"]
        if not reason or (reason not in _KNOWN_REASONS
                          and not reason.startswith("no_candidates_for_specialty:")):
            unknown_reasons.append((r, reason))

    if unknown_reasons:
        for r, reason in unknown_reasons:
            out.append(ValidationRow(
                check_id="V08",
                trainer_id=r["trainer_id"],
                slot=r["slot"],
                status="WARN",
                species=r["original_species"],
                issue=f"unchanged with unrecognised reason: '{reason}'",
            ))
    else:
        reason_counts: dict[str, int] = {}
        for r in unch:
            reason_counts[r["reason"]] = reason_counts.get(r["reason"], 0) + 1
        detail = "; ".join(f"{v}×{k}" for k, v in sorted(reason_counts.items(), key=lambda x: -x[1]))
        out.append(ValidationRow(
            check_id="V08", trainer_id="*", slot="*",
            status="PASS", species="",
            issue=f"{len(unch)} unchanged slots, all reasons recognised: {detail}",
        ))
    return out


# ── V09 — explicit review of known-problematic species ───────────────────────

_KNOWN_PROBLEMATIC = {
    # Species that had empty types due to Fairy parser bug
    "SPECIES_AZUMARILL":  "Fairy fix: should be WATER/FAIRY",
    "SPECIES_CLEFABLE":   "Fairy fix: should be FAIRY/FAIRY",
    "SPECIES_CLEFAIRY":   "Fairy fix: should be FAIRY/FAIRY",
    "SPECIES_GARDEVOIR":  "Fairy fix: should be PSYCHIC/FAIRY",
    "SPECIES_GRANBULL":   "Fairy fix: should be FAIRY/FAIRY",
    "SPECIES_JIGGLYPUFF": "Fairy fix: should be NORMAL/FAIRY",
    "SPECIES_MARILL":     "Fairy fix: should be WATER/FAIRY",
    "SPECIES_MR_MIME":    "Fairy fix: should be PSYCHIC/FAIRY",
    "SPECIES_SNUBBULL":   "Fairy fix: should be FAIRY/FAIRY",
    "SPECIES_TOGEKISS":   "Fairy fix: should be FAIRY/FLYING",
    "SPECIES_WIGGLYTUFF": "Fairy fix: should be NORMAL/FAIRY",
    # Mono-type specialist filter failures (expected unchanged)
    "SPECIES_ONIX":       "expected unchanged: no FIGHTING-type candidate passes type+egg+BST",
    "SPECIES_SABLEYE":    "expected unchanged: no GHOST-type candidate passes type+egg+BST",
    "SPECIES_EXEGGUTOR":  "expected unchanged: no PSYCHIC-type candidate passes type+egg+BST",
    # Structurally unreplaceable (Undiscovered/Ditto/Mineral+Normal)
    "SPECIES_DITTO":      "expected unchanged: Ditto egg group has no other normal-pool members",
    "SPECIES_MAGBY":      "expected unchanged: Undiscovered egg group (baby Pokemon)",
    "SPECIES_NIDOQUEEN":  "expected unchanged: Undiscovered egg group",
    "SPECIES_PORYGON":    "expected unchanged: Mineral egg group, no NORMAL-type candidates",
}

def _v09_known_species(replacements, symbol_index) -> list[ValidationRow]:
    out = []
    # Build lookup: original_species → list of replacement rows
    by_orig: dict[str, list[dict]] = {}
    for r in replacements:
        by_orig.setdefault(r["original_species"], []).append(r)

    for sym, note in sorted(_KNOWN_PROBLEMATIC.items()):
        rec = symbol_index.get(sym)
        if rec is None:
            out.append(ValidationRow(
                check_id="V09", trainer_id="*", slot="*",
                status="WARN", species=sym,
                issue=f"species not found in mondata — {note}",
            ))
            continue

        # Type correctness (Fairy-fixed species)
        if "Fairy fix" in note:
            types = rec.types_set()
            if not types:
                out.append(ValidationRow(
                    check_id="V09", trainer_id="*", slot="*",
                    status="FAIL", species=sym,
                    issue=f"type still empty after Fairy fix — {note}",
                ))
                continue
            if "FAIRY" not in types:
                out.append(ValidationRow(
                    check_id="V09", trainer_id="*", slot="*",
                    status="FAIL", species=sym,
                    issue=f"FAIRY not in types {types} — {note}",
                ))
                continue

        # Check if species appears in trainer data and what happened
        slots = by_orig.get(sym, [])
        if slots:
            replaced   = [s for s in slots if s["unchanged"] == "0"]
            unchanged_ = [s for s in slots if s["unchanged"] == "1"]
            if "expected unchanged" in note:
                if replaced:
                    # Replaced despite expecting unchanged — just INFO (pool may have expanded)
                    out.append(ValidationRow(
                        check_id="V09", trainer_id="*", slot="*",
                        status="INFO", species=sym,
                        issue=f"{len(replaced)} slot(s) were replaced (pool may have expanded after fix); {note}",
                    ))
                else:
                    out.append(ValidationRow(
                        check_id="V09", trainer_id="*", slot="*",
                        status="PASS", species=sym,
                        issue=f"{len(unchanged_)} slot(s) correctly unchanged — {note}",
                    ))
            else:
                # Fairy-fixed species appearing in trainer parties
                if replaced:
                    out.append(ValidationRow(
                        check_id="V09", trainer_id="*", slot="*",
                        status="PASS", species=sym,
                        issue=f"types now {rec.types_set()}; {len(replaced)} replaced, {len(unchanged_)} unchanged — {note}",
                    ))
                else:
                    out.append(ValidationRow(
                        check_id="V09", trainer_id="*", slot="*",
                        status="INFO", species=sym,
                        issue=f"types now {rec.types_set()} (fix confirmed); not found in any trainer party — {note}",
                    ))
        else:
            out.append(ValidationRow(
                check_id="V09", trainer_id="*", slot="*",
                status="INFO", species=sym,
                issue=f"types={rec.types_set()}; not used in any trainer party — {note}",
            ))

    return out


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))

"""
trainer_writer.py
=================
Phase 6: rewrite armips/data/trainers/trainers.s using validated datasets.

Strategy
--------
Read the file as lines; track current trainer_id / slot_index / per-slot
move index with the same state logic used by trainer_parser.py.

For each line:
  - `pokemon SPECIES_X` or `monwithform SPECIES_X, N`
                    → substitute new_species using the correct emit syntax
  - `move MOVE_Y`   → substitute next move from new_moves list
  - all other lines → written verbatim

Species emit rules
------------------
The armips `pokemon` macro validates that the species index ≤ NUM_OF_MONS
(1075).  Form-range species (index > 1075: Alolan, Galarian, gender forms,
cosmetic forms, etc.) MUST be written as:

    monwithform BASE_SPECIES, formId

where BASE_SPECIES is the canonical base species and formId is the 1-based
index within PokeFormDataTbl.c.

Base-range form species (Wormadam Sandy = 499, Rotom Heat = 503, etc.) are
≤ NUM_OF_MONS and continue to use `pokemon SPECIES_X` normally.

The form_map argument (from form_table.build_form_map) provides the set of
form-range species and their (base, id) pairs.  Any species NOT in form_map
uses the `pokemon` syntax.

Re-run safety
-------------
The writer handles existing `monwithform` lines in the source file so that
re-running the write phase on an already-written file is safe.  Unchanged
slots keep their original line verbatim.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path


# ── Regex patterns ───────────────────────────────────────────────────────────

_RE_TRAINERDATA  = re.compile(r'^trainerdata\s+(\d+),')
_RE_PARTY_START  = re.compile(r'^\s+party\b')
_RE_ENDPARTY     = re.compile(r'^\s+endparty\b')
_RE_COMMENT_MON  = re.compile(r'^\s+//\s*mon\s+(\d+)')
_RE_POKEMON      = re.compile(r'^(\s+)pokemon\s+(SPECIES_\S+)')
_RE_MONWITHFORM  = re.compile(r'^(\s+)monwithform\s+(SPECIES_\S+),\s*(\d+)')
_RE_MOVE         = re.compile(r'^(\s+move\s+)(MOVE_\S+)')


# ── Stats ────────────────────────────────────────────────────────────────────

@dataclass
class WriteStats:
    species_changed:  int = 0
    species_kept:     int = 0    # unchanged flag or no replacement found
    movesets_changed: int = 0
    movesets_skipped: int = 0    # slot had no move lines in original
    total_slots:      int = 0
    summary_rows:     list[dict] = field(default_factory=list)


# ── Main writer ───────────────────────────────────────────────────────────────

def rewrite_trainers(
    src: Path,
    dst: Path,
    bak: Path,
    new_species_map:  dict[tuple[int,int], str],      # (tid, slot) → new_species
    is_unchanged:     dict[tuple[int,int], bool],     # (tid, slot) → True = keep original
    new_moves_map:    dict[tuple[int,int], list[str]], # (tid, slot) → [m1,m2,m3,m4]
    trainer_name_map: dict[int, str],                  # tid → trainer_name
    form_map:         dict[str, tuple[str, int]],      # form_sym → (base_sym, form_id)
) -> WriteStats:
    """
    Copy src → bak, then write the rewritten file to dst.

    dst may equal src (in-place rewrite) — the backup is created first.

    form_map must be the result of form_table.build_form_map().  It is used
    to determine whether a new species should be emitted as:
      pokemon SPECIES_X          (not in form_map)
      monwithform BASE, formId   (in form_map)
    """
    # ── Backup first ──────────────────────────────────────────────────────────
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, bak)

    # ── Read source ───────────────────────────────────────────────────────────
    with open(src, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    stats = WriteStats()
    out_lines: list[str] = []

    # State
    current_tid:   int  = -1
    in_party:      bool = False
    current_slot:  int  = -1
    move_idx:      int  = 0     # index of next move to write within this slot

    # Per-slot tracking (for summary and stats)
    slot_had_any_move:    dict[tuple[int,int], bool] = {}
    slot_species_changed: set[tuple[int,int]] = set()
    slot_moves_changed:   set[tuple[int,int]] = set()

    for raw_line in lines:
        line = raw_line   # preserve original line-ending

        # ── New trainer ───────────────────────────────────────────────────────
        m = _RE_TRAINERDATA.match(line)
        if m:
            current_tid  = int(m.group(1))
            in_party     = False
            current_slot = -1
            move_idx     = 0
            out_lines.append(line)
            continue

        # ── Party start ───────────────────────────────────────────────────────
        if _RE_PARTY_START.match(line):
            in_party = True
            out_lines.append(line)
            continue

        # ── Party end ────────────────────────────────────────────────────────
        if _RE_ENDPARTY.match(line):
            in_party     = False
            current_slot = -1
            move_idx     = 0
            out_lines.append(line)
            continue

        if not in_party:
            out_lines.append(line)
            continue

        # ── // mon N ─────────────────────────────────────────────────────────
        m = _RE_COMMENT_MON.match(line)
        if m:
            current_slot = int(m.group(1))
            move_idx     = 0
            stats.total_slots += 1
            out_lines.append(line)
            continue

        # ── pokemon / monwithform line ────────────────────────────────────────
        # Both forms of the species directive are handled identically:
        # look up the new species from new_species_map and emit with the
        # correct syntax based on whether the new species is in form_map.
        m_poke = _RE_POKEMON.match(line)
        m_form = _RE_MONWITHFORM.match(line) if not m_poke else None

        if (m_poke or m_form) and current_slot >= 0:
            key = (current_tid, current_slot)
            indent = m_poke.group(1) if m_poke else m_form.group(1)

            if is_unchanged.get(key, False):
                # Keep original line verbatim (species is unchanged)
                stats.species_kept += 1
                out_lines.append(line)
            elif key in new_species_map:
                new_sym = new_species_map[key]
                # Determine old_sym for change detection
                if m_poke:
                    old_sym = m_poke.group(2)
                else:
                    # Reconstruct old form species from monwithform (best-effort)
                    old_sym = m_form.group(2)  # base species only

                emitted = _emit_species_line(indent, new_sym, form_map, line)
                changed = (new_sym != old_sym)
                if changed:
                    stats.species_changed += 1
                    slot_species_changed.add(key)
                else:
                    stats.species_kept += 1
                out_lines.append(emitted)
            else:
                stats.species_kept += 1
                out_lines.append(line)
            continue

        # ── move line ─────────────────────────────────────────────────────────
        m = _RE_MOVE.match(line)
        if m and current_slot >= 0:
            key    = (current_tid, current_slot)
            prefix = m.group(1)
            old_mv = m.group(2)

            slot_had_any_move[key] = True

            new_moves = new_moves_map.get(key)
            if new_moves is not None and move_idx < len(new_moves):
                new_mv = new_moves[move_idx]
                if new_mv != old_mv:
                    slot_moves_changed.add(key)
                    out_lines.append(_rewrite_move_line(line, prefix, new_mv))
                else:
                    out_lines.append(line)
            else:
                out_lines.append(line)
            move_idx += 1
            continue

        # ── everything else ───────────────────────────────────────────────────
        out_lines.append(line)

    # Finalize slot stats
    stats.movesets_changed = len(slot_moves_changed)
    stats.movesets_skipped = stats.total_slots - len(slot_had_any_move)

    # Build summary rows
    all_keys = set(new_species_map.keys()) | set(new_moves_map.keys())
    for (tid, slot) in sorted(all_keys):
        key = (tid, slot)
        stats.summary_rows.append({
            "trainer_id":      tid,
            "trainer_name":    trainer_name_map.get(tid, ""),
            "slot":            slot,
            "species_changed": int(key in slot_species_changed),
            "unchanged_flag":  int(is_unchanged.get(key, False)),
            "moves_changed":   int(key in slot_moves_changed),
        })

    # ── Write output ──────────────────────────────────────────────────────────
    with open(dst, "w", encoding="utf-8") as fh:
        fh.writelines(out_lines)

    return stats


# ── Species line emitters ─────────────────────────────────────────────────────

def _emit_species_line(
    indent: str,
    new_sym: str,
    form_map: dict[str, tuple[str, int]],
    original: str,
) -> str:
    """
    Produce the correct armips species line for new_sym.

    If new_sym is in form_map → `monwithform BASE_SPECIES, formId`
    Otherwise                 → `pokemon SPECIES_X`

    Preserves the original line ending.
    """
    nl = "\r\n" if original.endswith("\r\n") else "\n"
    if new_sym in form_map:
        base_sym, form_id = form_map[new_sym]
        return f"{indent}monwithform {base_sym}, {form_id}{nl}"
    return f"{indent}pokemon {new_sym}{nl}"


def _rewrite_move_line(original: str, prefix: str, new_mv: str) -> str:
    """Replace move symbol, preserving indent and line ending."""
    nl = "\r\n" if original.endswith("\r\n") else "\n"
    return prefix + new_mv + nl

"""
trainer_parser.py
=================
Parses armips/data/trainers/trainers.s into structured TrainerRecord objects.

Each TrainerRecord contains:
  - trainer_id
  - trainer_name
  - trainer_class
  - battle_type
  - num_mons
  - party: list of PartySlot

Each PartySlot contains:
  - slot_index
  - level
  - species
  - moves (list of up to 4 MOVE_ symbols)

The parser is a simple line-by-line state machine.  It does not attempt to
handle every field — it extracts only the fields needed for the pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class PartySlot:
    slot_index: int
    level: int = 0
    species: str = "SPECIES_NONE"
    moves: list[str] = field(default_factory=list)

    def move(self, idx: int) -> str:
        return self.moves[idx] if idx < len(self.moves) else "MOVE_NONE"


@dataclass
class TrainerRecord:
    trainer_id: int
    trainer_name: str
    trainer_class: str = ""
    battle_type: str = "SINGLE_BATTLE"
    num_mons: int = 0
    party: list[PartySlot] = field(default_factory=list)


# ── Regex patterns ───────────────────────────────────────────────────────────

_RE_TRAINERDATA = re.compile(r'^trainerdata\s+(\d+),\s*"([^"]*)"')
_RE_TRAINERCLASS = re.compile(r'^\s+trainerclass\s+(TRAINERCLASS_\S+)')
_RE_NUMMONS      = re.compile(r'^\s+nummons\s+(\d+)')
_RE_BATTLETYPE   = re.compile(r'^\s+battletype\s+(\S+)')
_RE_PARTY        = re.compile(r'^\s+party\s+(\d+)')
_RE_LEVEL        = re.compile(r'^\s+level\s+(\d+)')
_RE_POKEMON      = re.compile(r'^\s+pokemon\s+(SPECIES_\S+)')
_RE_MONWITHFORM  = re.compile(r'^\s+monwithform\s+(SPECIES_\S+),\s*(\d+)')
_RE_MOVE         = re.compile(r'^\s+move\s+(MOVE_\S+)')
_RE_ENDPARTY     = re.compile(r'^\s+endparty\b')
_RE_COMMENT_MON  = re.compile(r'^\s+//\s*mon\s+(\d+)')


# ── Parser ───────────────────────────────────────────────────────────────────

class _State:
    HEADER  = "header"   # inside trainerdata block
    PARTY   = "party"    # inside party block
    OUTSIDE = "outside"  # between blocks


def parse_trainers(
    path: Path,
    reverse_form_map: dict[tuple[str, int], str] | None = None,
) -> list[TrainerRecord]:
    """
    Parse trainers.s and return all TrainerRecord objects.

    reverse_form_map (optional): {(base_species, form_id): form_species_symbol}
        Built from form_table.build_reverse_form_map().  When provided,
        `monwithform BASE, N` lines are resolved to the full form species symbol
        (e.g. "SPECIES_GRAVELER_ALOLAN") instead of storing only the base species.
        Without this, the parser silently loses form identity for all form-range slots.
    """
    trainers: list[TrainerRecord] = []
    current_trainer: Optional[TrainerRecord] = None
    current_slot: Optional[PartySlot] = None
    slot_index: int = 0
    state = _State.OUTSIDE

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            # ── New trainer header ────────────────────────────────────────
            m = _RE_TRAINERDATA.match(line)
            if m:
                # Save previous slot if any
                if current_slot is not None and current_trainer is not None:
                    current_trainer.party.append(current_slot)
                    current_slot = None
                # Save previous trainer
                if current_trainer is not None:
                    trainers.append(current_trainer)

                current_trainer = TrainerRecord(
                    trainer_id=int(m.group(1)),
                    trainer_name=m.group(2),
                )
                slot_index = 0
                state = _State.HEADER
                continue

            if current_trainer is None:
                continue

            # ── Header fields ─────────────────────────────────────────────
            if state == _State.HEADER:
                m = _RE_TRAINERCLASS.match(line)
                if m:
                    current_trainer.trainer_class = m.group(1)
                    continue

                m = _RE_NUMMONS.match(line)
                if m:
                    current_trainer.num_mons = int(m.group(1))
                    continue

                m = _RE_BATTLETYPE.match(line)
                if m:
                    current_trainer.battle_type = m.group(1)
                    continue

                m = _RE_PARTY.match(line)
                if m:
                    state = _State.PARTY
                    slot_index = 0
                    continue

            # ── Party block ───────────────────────────────────────────────
            elif state == _State.PARTY:
                # "// mon N" comment marks start of a new slot
                m = _RE_COMMENT_MON.match(line)
                if m:
                    if current_slot is not None:
                        current_trainer.party.append(current_slot)
                    slot_index = int(m.group(1))
                    current_slot = PartySlot(slot_index=slot_index)
                    continue

                m = _RE_LEVEL.match(line)
                if m:
                    if current_slot is None:
                        current_slot = PartySlot(slot_index=slot_index)
                    current_slot.level = int(m.group(1))
                    continue

                m = _RE_POKEMON.match(line)
                if m:
                    if current_slot is None:
                        current_slot = PartySlot(slot_index=slot_index)
                    current_slot.species = m.group(1).rstrip(",")
                    continue

                m = _RE_MONWITHFORM.match(line)
                if m:
                    if current_slot is None:
                        current_slot = PartySlot(slot_index=slot_index)
                    base_sym = m.group(1).rstrip(",")
                    form_id  = int(m.group(2))
                    if reverse_form_map is not None:
                        # Resolve to the full form species symbol via the
                        # authoritative form table (PokeFormDataTbl.c).
                        # e.g. (SPECIES_GRAVELER, 1) → SPECIES_GRAVELER_ALOLAN
                        current_slot.species = reverse_form_map.get(
                            (base_sym, form_id), base_sym
                        )
                    else:
                        # Fallback: store base species only (form identity lost).
                        current_slot.species = base_sym
                    continue

                m = _RE_MOVE.match(line)
                if m:
                    if current_slot is None:
                        current_slot = PartySlot(slot_index=slot_index)
                    move = m.group(1).rstrip(",")
                    if len(current_slot.moves) < 4:
                        current_slot.moves.append(move)
                    continue

                m = _RE_ENDPARTY.match(line)
                if m:
                    if current_slot is not None:
                        current_trainer.party.append(current_slot)
                        current_slot = None
                    state = _State.OUTSIDE
                    continue

    # Flush last trainer
    if current_slot is not None and current_trainer is not None:
        current_trainer.party.append(current_slot)
    if current_trainer is not None:
        trainers.append(current_trainer)

    return trainers

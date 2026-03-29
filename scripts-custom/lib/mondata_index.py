"""
mondata_index.py
================
Parses armips/data/mondata.s and builds a list of SpeciesRecord objects.

Each record captures:
  - species symbol
  - display name
  - HP / Atk / Def / Spe / SpA / SpD / BST
  - type1 / type2  (TYPE_ prefix stripped)
  - egggroup1 / egggroup2  (EGG_GROUP_ prefix stripped)
  - form_type
  - base_form_group
  - category_group
  - excluded_from_normal_pool
  - exclusion_reason

Parsing strategy:
  Each mondata block opens with ^mondata SPECIES_X, "name" and contains
  indented field lines until the next mondata/EOF.  We iterate
  line-by-line and accumulate fields into the current record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .species_rules import (
    detect_form_type,
    base_form_group as compute_base_form_group,
    get_category,
    is_excluded_from_normal_pool,
)

# ── Regex patterns ───────────────────────────────────────────────────────────

_RE_MONDATA    = re.compile(r'^mondata\s+(SPECIES_\S+),\s*"([^"]*)"')
_RE_BASESTATS  = re.compile(r'^\s+basestats\s+(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)')
_RE_TYPES_LINE = re.compile(r'^\s+types\s+(.+)')        # captures raw type expressions
_RE_EGGGROUPS  = re.compile(r'^\s+egggroups\s+(EGG_GROUP_\S+),\s*(EGG_GROUP_\S+)')

# Matches: `(FAIRY_TYPE_IMPLEMENTED) ? TYPE_A : TYPE_B`
#      or: `FAIRY_TYPE_IMPLEMENTED ? TYPE_A : TYPE_B`   (no outer parens)
# Since FAIRY_TYPE_IMPLEMENTED == 1 in this project, we resolve to the true branch (TYPE_A).
_RE_COND_TYPE  = re.compile(
    r'\(?FAIRY_TYPE_IMPLEMENTED\)?\s*\?\s*(TYPE_\w+)\s*:\s*TYPE_\w+'
)


def _resolve_type_expr(raw: str) -> str:
    """
    Resolve one raw type expression to a plain TYPE_ symbol.

    Handles:
      - plain `TYPE_FIRE`
      - `(FAIRY_TYPE_IMPLEMENTED) ? TYPE_FAIRY : TYPE_NORMAL`
      - `FAIRY_TYPE_IMPLEMENTED ? TYPE_FAIRY : TYPE_NORMAL`   (no parens)

    FAIRY_TYPE_IMPLEMENTED is treated as 1 (true) per include/config.h.
    Returns empty string if the expression cannot be resolved.
    """
    token = raw.strip().rstrip(",")
    m = _RE_COND_TYPE.search(token)
    if m:
        return m.group(1)           # true branch
    m = re.match(r"TYPE_\w+", token)
    if m:
        return m.group(0)
    return ""


@dataclass
class SpeciesRecord:
    symbol: str
    display_name: str
    hp: int = 0
    atk: int = 0
    def_: int = 0
    spe: int = 0
    spa: int = 0
    spd: int = 0
    bst: int = 0
    type1: str = ""
    type2: str = ""
    egggroup1: str = ""
    egggroup2: str = ""
    form_type: str = "base"
    base_form_group: str = ""
    category_group: str = "normal"
    excluded_from_normal_pool: bool = False
    exclusion_reason: str = ""

    def finalize(self) -> None:
        """Compute derived fields after all raw data has been populated."""
        self.bst = self.hp + self.atk + self.def_ + self.spe + self.spa + self.spd
        self.form_type = detect_form_type(self.symbol, self.display_name)
        self.base_form_group = compute_base_form_group(self.symbol)
        self.category_group = get_category(self.symbol)
        excl, reason = is_excluded_from_normal_pool(self.symbol, self.form_type)
        self.excluded_from_normal_pool = excl
        self.exclusion_reason = reason

    def types_set(self) -> frozenset[str]:
        return frozenset(t for t in (self.type1, self.type2) if t)

    def egggroups_set(self) -> frozenset[str]:
        return frozenset(g for g in (self.egggroup1, self.egggroup2) if g and g != "NONE")


def _strip_type_prefix(raw: str) -> str:
    """'TYPE_FIRE' → 'FIRE', handles trailing commas or whitespace."""
    return raw.replace("TYPE_", "").strip().rstrip(",")


def _strip_egg_prefix(raw: str) -> str:
    """'EGG_GROUP_MONSTER' → 'MONSTER'."""
    return raw.replace("EGG_GROUP_", "").strip().rstrip(",")


def parse_mondata(path: Path) -> list[SpeciesRecord]:
    """
    Parse mondata.s and return a list of SpeciesRecord (SPECIES_NONE excluded).

    Temporal assumption: the six basestats values are in order:
      HP, Atk, Def, Spe, SpA, SpD
    This matches the order documented in the report and confirmed from
    Bulbasaur's known stats (45/49/49/45/65/65 → BST 318).
    """
    records: list[SpeciesRecord] = []
    current: Optional[SpeciesRecord] = None

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            # New mondata block?
            m = _RE_MONDATA.match(line)
            if m:
                if current is not None and current.symbol != "SPECIES_NONE":
                    current.finalize()
                    records.append(current)
                symbol = m.group(1).rstrip(",")
                name   = m.group(2)
                current = SpeciesRecord(symbol=symbol, display_name=name)
                continue

            if current is None:
                continue

            # basestats
            m = _RE_BASESTATS.match(line)
            if m:
                hp, atk, def_, spe, spa, spd = (int(x) for x in m.groups())
                current.hp   = hp
                current.atk  = atk
                current.def_ = def_
                current.spe  = spe
                current.spa  = spa
                current.spd  = spd
                continue

            # types — may contain conditional expressions like
            # `(FAIRY_TYPE_IMPLEMENTED) ? TYPE_FAIRY : TYPE_NORMAL`
            m = _RE_TYPES_LINE.match(line)
            if m:
                raw = m.group(1)
                comma_idx = raw.find(",")
                if comma_idx >= 0:
                    t1 = _resolve_type_expr(raw[:comma_idx])
                    t2 = _resolve_type_expr(raw[comma_idx + 1:])
                    if t1:
                        current.type1 = _strip_type_prefix(t1)
                    if t2:
                        current.type2 = _strip_type_prefix(t2)
                continue

            # egggroups
            m = _RE_EGGGROUPS.match(line)
            if m:
                current.egggroup1 = _strip_egg_prefix(m.group(1))
                current.egggroup2 = _strip_egg_prefix(m.group(2))
                continue

    # Flush last record
    if current is not None and current.symbol != "SPECIES_NONE":
        current.finalize()
        records.append(current)

    return records


def build_symbol_index(records: list[SpeciesRecord]) -> dict[str, SpeciesRecord]:
    """Return a {symbol: record} lookup dict."""
    return {r.symbol: r for r in records}

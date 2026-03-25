#!/usr/bin/env python3
"""
normalize_trainers.py

Normalizes every trainer in armips/data/trainers/trainers.s to use the
full template structure from armips/data/trainers/trainers_template.s.

Rules applied:
  - trainermontype  → full flag set (ITEMS|MOVES|ABILITY|BALL|IV_EV_SET|NATURE_SET|SHINY_LOCK|0)
  - aiflags         → Red's flags (F_PRIORITIZE_SUPER_EFFECTIVE|F_EVALUATE_ATTACKS|F_EXPERT_ATTACKS|0)
  - battletype      → preserved as-is
  - item (held)     → ITEM_NONE if missing
  - moves (4x)      → kept if present; generated from learnset if absent
  - ability         → resolved from abilityslot + mondata abilities
  - ball            → ITEM_POKE_BALL
  - setivs          → ivs_value × 6 (value replicated into all six slots)
  - setevs          → 0 × 6
  - nature          → deterministic hash: MD5("nature_<trainer>_<monidx>") % 25
  - shinylock       → 1 if MD5("shiny_<trainer>_<monidx>") % 512 == 0, else 0

Output is written in-place (overwrites trainers.s).
"""

import json
import re
import hashlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
TRAINERS_S   = ROOT / "armips/data/trainers/trainers.s"
MONDATA_S    = ROOT / "armips/data/mondata.s"
LEARNSETS_J  = ROOT / "data/learnsets/learnsets.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FULL_MONTYPE = (
    "TRAINER_DATA_TYPE_ITEMS | TRAINER_DATA_TYPE_MOVES | "
    "TRAINER_DATA_TYPE_ABILITY | TRAINER_DATA_TYPE_BALL | "
    "TRAINER_DATA_TYPE_IV_EV_SET | TRAINER_DATA_TYPE_NATURE_SET | "
    "TRAINER_DATA_TYPE_SHINY_LOCK | 0"
)

RED_AIFLAGS = "F_PRIORITIZE_SUPER_EFFECTIVE | F_EVALUATE_ATTACKS | F_EXPERT_ATTACKS | 0"

NATURES = [
    "NATURE_HARDY",   "NATURE_LONELY",  "NATURE_BRAVE",   "NATURE_ADAMANT", "NATURE_NAUGHTY",
    "NATURE_BOLD",    "NATURE_DOCILE",  "NATURE_RELAXED", "NATURE_IMPISH",  "NATURE_LAX",
    "NATURE_TIMID",   "NATURE_HASTY",   "NATURE_SERIOUS", "NATURE_JOLLY",   "NATURE_NAIVE",
    "NATURE_MODEST",  "NATURE_MILD",    "NATURE_QUIET",   "NATURE_BASHFUL", "NATURE_RASH",
    "NATURE_CALM",    "NATURE_GENTLE",  "NATURE_SASSY",   "NATURE_CAREFUL", "NATURE_QUIRKY",
]

# ---------------------------------------------------------------------------
# Deterministic helpers
# ---------------------------------------------------------------------------
def _h(tag: str, trainer_id: int, mon_idx: int) -> int:
    data = f"{tag}_{trainer_id}_{mon_idx}".encode()
    return int(hashlib.md5(data).hexdigest()[:8], 16)

def nature_for(trainer_id: int, mon_idx: int) -> str:
    return NATURES[_h("nature", trainer_id, mon_idx) % 25]

def shinylock_for(trainer_id: int, mon_idx: int) -> int:
    return 1 if _h("shiny", trainer_id, mon_idx) % 512 == 0 else 0

# ---------------------------------------------------------------------------
# Load mondata.s  →  {SPECIES_NAME: (ability1, ability2)}
# ---------------------------------------------------------------------------
def load_abilities() -> dict:
    abilities: dict = {}
    current_species = None
    with open(MONDATA_S) as f:
        for line in f:
            s = line.strip()
            m = re.match(r'mondata\s+(SPECIES_\w+)\s*,', s)
            if m:
                current_species = m.group(1)
            elif current_species:
                m = re.match(r'abilities\s+(ABILITY_\w+)\s*,\s*(ABILITY_\w+)', s)
                if m:
                    abilities[current_species] = (m.group(1), m.group(2))
                    current_species = None  # one abilities line per mondata block
    return abilities

def resolve_ability(species: str, abilityslot: str, abilities: dict) -> str:
    pair = abilities.get(species, ("ABILITY_NONE", "ABILITY_NONE"))
    slot = int(abilityslot)
    if slot == 0:
        return pair[0]
    # 32 = second regular ability
    ab = pair[1]
    return ab if ab and ab != "" else "ABILITY_NONE"

# ---------------------------------------------------------------------------
# Load learnsets.json  →  {SPECIES_NAME: [(level, move_name), ...]}
# ---------------------------------------------------------------------------
def load_learnsets() -> dict:
    with open(LEARNSETS_J) as f:
        raw = json.load(f)
    return {sp: [(e["Level"], e["Move"]) for e in data.get("LevelMoves", [])]
            for sp, data in raw.items()}

def moves_for(species: str, level: int, learnsets: dict) -> list:
    """Return the last 4 moves learned at or before `level`, padded with MOVE_NONE."""
    entries = learnsets.get(species, [])
    learned = [mv for (lv, mv) in entries if lv <= level]
    last4 = learned[-4:] if len(learned) >= 4 else learned
    return last4 + ["MOVE_NONE"] * (4 - len(last4))

# ---------------------------------------------------------------------------
# Data model for a single Pokémon in a trainer party
# ---------------------------------------------------------------------------
class Mon:
    __slots__ = ("comment", "ivs", "abilityslot", "level",
                 "pokemon", "item", "moves", "ballseal")

    def __init__(self):
        self.comment     = ""
        self.ivs         = "0"
        self.abilityslot = "0"
        self.level       = "5"
        self.pokemon     = "SPECIES_NONE"
        self.item        = None   # None = not present in source
        self.moves       = None   # None = not present; list[str] if present
        self.ballseal    = "0"

# ---------------------------------------------------------------------------
# Data model for a trainer entry
# ---------------------------------------------------------------------------
class Trainer:
    __slots__ = ("number", "name", "trainermontype", "trainerclass",
                 "nummons", "bag_items", "aiflags", "battletype", "mons")

    def __init__(self):
        self.number         = 0
        self.name           = ""
        self.trainermontype = ""
        self.trainerclass   = ""
        self.nummons        = "0"
        self.bag_items      = []
        self.aiflags        = ""
        self.battletype     = "SINGLE_BATTLE"
        self.mons           = []

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def parse_file(path: Path):
    """Return (header_lines: list[str], trainers: list[Trainer])."""
    with open(path) as f:
        lines = f.readlines()

    header: list   = []
    trainers: list = []
    trainer        = None
    mon            = None
    in_party       = False

    for raw in lines:
        s = raw.strip()

        # ── Header (everything before the first trainerdata) ──────────────
        if not trainers and not re.match(r'trainerdata\s+\d+', s):
            header.append(raw)
            continue

        # ── trainerdata N, "Name" ─────────────────────────────────────────
        m = re.match(r'trainerdata\s+(\d+)\s*,\s*"([^"]*)"', s)
        if m:
            trainer    = Trainer()
            trainer.number = int(m.group(1))
            trainer.name   = m.group(2)
            trainers.append(trainer)
            in_party = False
            mon      = None
            continue

        if trainer is None:
            continue

        # ── Inside trainerdata...endentry ─────────────────────────────────
        if not in_party:
            if s.startswith("trainermontype"):
                trainer.trainermontype = s[len("trainermontype"):].strip()
            elif s.startswith("trainerclass"):
                trainer.trainerclass = s[len("trainerclass"):].strip()
            elif s.startswith("nummons"):
                trainer.nummons = s[len("nummons"):].strip()
            elif s.startswith("item"):
                trainer.bag_items.append(s[len("item"):].strip())
            elif s.startswith("aiflags"):
                trainer.aiflags = s[len("aiflags"):].strip()
            elif s.startswith("battletype"):
                trainer.battletype = s[len("battletype"):].strip()
            elif s == "endentry":
                pass
            elif re.match(r'party\s+\d+', s):
                in_party = True
            continue

        # ── Inside party...endparty ───────────────────────────────────────
        if s == "endparty":
            if mon is not None:
                trainer.mons.append(mon)
                mon = None
            in_party = False
            continue

        if re.match(r'//\s*mon\s+\d+', s):
            if mon is not None:
                trainer.mons.append(mon)
            mon = Mon()
            mon.comment = s
            continue

        if mon is None:
            continue

        if s.startswith("ivs"):
            mon.ivs = s[len("ivs"):].strip()
        elif s.startswith("abilityslot"):
            mon.abilityslot = s[len("abilityslot"):].strip()
        elif s.startswith("level"):
            mon.level = s[len("level"):].strip()
        elif s.startswith("pokemon"):
            mon.pokemon = s[len("pokemon"):].strip()
        elif s.startswith("item"):
            mon.item = s[len("item"):].strip()
        elif s.startswith("move"):
            if mon.moves is None:
                mon.moves = []
            mon.moves.append(s[len("move"):].strip())
        elif s.startswith("ballseal"):
            mon.ballseal = s[len("ballseal"):].strip()

    return header, trainers

# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
I4 = "    "   # 4-space indent (trainer fields)
I8 = "        "  # 8-space indent (party fields)

def render_trainer(t: Trainer, abilities: dict, learnsets: dict) -> str:
    out = []

    # ── Trainer entry ──────────────────────────────────────────────────────
    out.append(f'trainerdata {t.number}, "{t.name}"\n')
    out.append(f'{I4}trainermontype {FULL_MONTYPE}\n')
    out.append(f'{I4}trainerclass {t.trainerclass}\n')
    out.append(f'{I4}nummons {t.nummons}\n')
    # Ensure exactly 4 bag items
    bag = list(t.bag_items)
    while len(bag) < 4:
        bag.append("ITEM_NONE")
    for bi in bag[:4]:
        out.append(f'{I4}item {bi}\n')
    out.append(f'{I4}aiflags {RED_AIFLAGS}\n')
    out.append(f'{I4}battletype {t.battletype}\n')
    out.append(f'{I4}endentry\n')
    out.append('\n')

    # ── Party ──────────────────────────────────────────────────────────────
    out.append(f'{I4}party {t.number}\n')

    for idx, mon in enumerate(t.mons):
        out.append(f'{I8}{mon.comment}\n')

        iv_val = mon.ivs

        # held item
        held = mon.item if mon.item is not None else "ITEM_NONE"

        # moves: kept if present, generated if absent
        if mon.moves is not None:
            # Normalise to exactly 4 entries
            mv = list(mon.moves)
            while len(mv) < 4:
                mv.append("MOVE_NONE")
            mv = mv[:4]
        else:
            level_int = int(mon.level) if mon.level.isdigit() else 0
            mv = moves_for(mon.pokemon, level_int, learnsets)

        # ability
        ability = resolve_ability(mon.pokemon, mon.abilityslot, abilities)

        # setivs: replicate the single ivs value across all six slots
        sv = iv_val

        # deterministic nature & shinylock
        nat  = nature_for(t.number, idx)
        lock = shinylock_for(t.number, idx)

        out.append(f'{I8}ivs {iv_val}\n')
        out.append(f'{I8}abilityslot {mon.abilityslot}\n')
        out.append(f'{I8}level {mon.level}\n')
        out.append(f'{I8}pokemon {mon.pokemon}\n')
        out.append(f'{I8}item {held}\n')
        for m in mv:
            out.append(f'{I8}move {m}\n')
        out.append(f'{I8}ability {ability}\n')
        out.append(f'{I8}ball ITEM_POKE_BALL\n')
        out.append(f'{I8}setivs {sv}, {sv}, {sv}, {sv}, {sv}, {sv}\n')
        out.append(f'{I8}setevs 0, 0, 0, 0, 0, 0\n')
        out.append(f'{I8}nature {nat}\n')
        out.append(f'{I8}shinylock {lock}\n')
        out.append(f'{I8}ballseal {mon.ballseal}\n')

    out.append(f'{I4}endparty\n')
    out.append('\n')

    return "".join(out)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading ability data from mondata.s ...")
    abilities = load_abilities()
    print(f"  → {len(abilities)} species loaded.")

    print("Loading learnsets from learnsets.json ...")
    learnsets = load_learnsets()
    print(f"  → {len(learnsets)} species loaded.")

    print("Parsing trainers.s ...")
    header, trainers = parse_file(TRAINERS_S)
    print(f"  → {len(trainers)} trainer entries parsed.")

    print("Generating normalized output ...")
    out_parts = header[:]
    for t in trainers:
        out_parts.append(render_trainer(t, abilities, learnsets))

    output = "".join(out_parts)

    # Write in-place (keep a .bak just in case)
    bak = TRAINERS_S.with_suffix(".s.bak")
    TRAINERS_S.rename(bak)
    TRAINERS_S.write_text(output, encoding="utf-8")
    print(f"Done. Wrote {TRAINERS_S}")
    print(f"Backup saved to {bak}")

    # Quick sanity stats
    total_mons = sum(len(t.mons) for t in trainers)
    shiny_ones = sum(
        shinylock_for(t.number, i)
        for t in trainers
        for i, _ in enumerate(t.mons)
    )
    print(f"\nStats:")
    print(f"  Trainers: {len(trainers)}")
    print(f"  Total Pokémon slots: {total_mons}")
    print(f"  Shinylock=1 slots: {shiny_ones}  ({shiny_ones}/{total_mons} ≈ 1/{total_mons//shiny_ones if shiny_ones else '∞'})")

if __name__ == "__main__":
    main()

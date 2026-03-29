"""
species_rules.py
================
Category classification and form-type detection for mondata species.

Mirrors the IS_SPECIES_* macros in include/pokemon.h exactly.
These sets drive pool exclusion rules: normal species cannot become
legendary/mythical/sublegend/ultra-beast/paradox, and excluded-category
sources must be replaced from the same category group.
"""

# ── Category sets (ported from include/pokemon.h) ──────────────────────────

LEGENDARY = frozenset({
    "SPECIES_MEWTWO", "SPECIES_LUGIA", "SPECIES_HO_OH",
    "SPECIES_KYOGRE", "SPECIES_GROUDON", "SPECIES_RAYQUAZA",
    "SPECIES_DIALGA", "SPECIES_PALKIA", "SPECIES_GIRATINA",
    "SPECIES_RESHIRAM", "SPECIES_ZEKROM", "SPECIES_KYUREM",
    "SPECIES_XERNEAS", "SPECIES_YVELTAL", "SPECIES_ZYGARDE",
    "SPECIES_COSMOG", "SPECIES_COSMOEM", "SPECIES_SOLGALEO", "SPECIES_LUNALA",
    "SPECIES_NECROZMA",
    "SPECIES_ZACIAN", "SPECIES_ZAMAZENTA", "SPECIES_ETERNATUS",
    "SPECIES_CALYREX", "SPECIES_KORAIDON", "SPECIES_MIRAIDON",
    "SPECIES_TERAPAGOS",
})

MYTHICAL = frozenset({
    "SPECIES_MEW", "SPECIES_CELEBI", "SPECIES_JIRACHI", "SPECIES_DEOXYS",
    "SPECIES_PHIONE", "SPECIES_MANAPHY", "SPECIES_DARKRAI",
    "SPECIES_SHAYMIN", "SPECIES_ARCEUS",
    "SPECIES_VICTINI", "SPECIES_KELDEO", "SPECIES_MELOETTA", "SPECIES_GENESECT",
    "SPECIES_DIANCIE", "SPECIES_HOOPA", "SPECIES_VOLCANION",
    "SPECIES_MAGEARNA", "SPECIES_ZERAORA",
    "SPECIES_MELTAN", "SPECIES_MELMETAL",
    "SPECIES_ZARUDE", "SPECIES_PECHARUNT",
    # EXTRA_MYTHICALS (VANILLA_MYTHICALS: Shiinotic; else: Marshadow)
    "SPECIES_SHIINOTIC", "SPECIES_MARSHADOW",
})

SUBLEGEND = frozenset({
    "SPECIES_ARTICUNO", "SPECIES_ZAPDOS", "SPECIES_MOLTRES",
    "SPECIES_RAIKOU", "SPECIES_ENTEI", "SPECIES_SUICUNE",
    "SPECIES_REGIROCK", "SPECIES_REGICE", "SPECIES_REGISTEEL",
    "SPECIES_LATIAS", "SPECIES_LATIOS",
    "SPECIES_UXIE", "SPECIES_MESPRIT", "SPECIES_AZELF",
    "SPECIES_HEATRAN", "SPECIES_REGIGIGAS", "SPECIES_CRESSELIA",
    "SPECIES_COBALION", "SPECIES_TERRAKION", "SPECIES_VIRIZION",
    "SPECIES_TORNADUS", "SPECIES_THUNDURUS", "SPECIES_LANDORUS",
    "SPECIES_TYPE_NULL", "SPECIES_SILVALLY",
    "SPECIES_TAPU_KOKO", "SPECIES_TAPU_LELE", "SPECIES_TAPU_BULU", "SPECIES_TAPU_FINI",
    "SPECIES_KUBFU", "SPECIES_URSHIFU",
    "SPECIES_REGIELEKI", "SPECIES_REGIDRAGO",
    "SPECIES_GLASTRIER", "SPECIES_SPECTRIER",
    "SPECIES_ENAMORUS",
    "SPECIES_TING_LU", "SPECIES_CHIEN_PAO", "SPECIES_WO_CHIEN", "SPECIES_CHI_YU",
    "SPECIES_OGERPON",
    "SPECIES_OKIDOGI", "SPECIES_MUNKIDORI", "SPECIES_FEZANDIPITI",
})

ULTRA_BEAST = frozenset({
    "SPECIES_NIHILEGO", "SPECIES_BUZZWOLE", "SPECIES_PHEROMOSA",
    "SPECIES_XURKITREE", "SPECIES_CELESTEELA", "SPECIES_KARTANA",
    "SPECIES_GUZZLORD",
    "SPECIES_POIPOLE", "SPECIES_NAGANADEL",
    "SPECIES_STAKATAKA", "SPECIES_BLACEPHALON",
})

# Base Paradox set (always active regardless of config)
PARADOX_BASE = frozenset({
    "SPECIES_GREAT_TUSK", "SPECIES_SCREAM_TAIL", "SPECIES_BRUTE_BONNET",
    "SPECIES_FLUTTER_MANE", "SPECIES_SLITHER_WING", "SPECIES_SANDY_SHOCKS",
    "SPECIES_IRON_TREADS", "SPECIES_IRON_BUNDLE", "SPECIES_IRON_HANDS",
    "SPECIES_IRON_JUGULIS", "SPECIES_IRON_MOTH", "SPECIES_IRON_THORNS",
    "SPECIES_ROARING_MOON", "SPECIES_IRON_VALIANT",
    "SPECIES_WALKING_WAKE", "SPECIES_IRON_LEAVES",
})

# Extra Paradox forms (active when VANILLA_PARADOX_BOOSTER_ENERGY_BEHAVIOUR is off)
PARADOX_EXTRA = frozenset({
    "SPECIES_GOUGING_FIRE", "SPECIES_RAGING_BOLT",
    "SPECIES_IRON_BOULDER", "SPECIES_IRON_CROWN",
})

PARADOX = PARADOX_BASE | PARADOX_EXTRA

ALL_EXCLUDED = LEGENDARY | MYTHICAL | SUBLEGEND | ULTRA_BEAST | PARADOX


def get_category(species_symbol: str) -> str:
    """
    Return the category group label for a species symbol.
    Returns "normal" for species not in any excluded category.
    """
    if species_symbol in LEGENDARY:
        return "legendary"
    if species_symbol in MYTHICAL:
        return "mythical"
    if species_symbol in SUBLEGEND:
        return "sublegend"
    if species_symbol in ULTRA_BEAST:
        return "ultra_beast"
    if species_symbol in PARADOX:
        return "paradox"
    return "normal"


def is_excluded_from_normal_pool(species_symbol: str, form_type: str) -> tuple[bool, str]:
    """
    Return (excluded: bool, reason: str).
    A species is excluded from the normal candidate pool if it belongs to an
    excluded category, is a mega/gmax/primal form, or is a stub form variant.
    """
    cat = get_category(species_symbol)
    if cat != "normal":
        return True, cat

    if form_type in ("mega", "gmax", "primal", "stub_form", "alt_form", "battle_form"):
        return True, form_type

    return False, ""


# ── Form-type detection ─────────────────────────────────────────────────────

# Keywords that identify form variants from their SPECIES_ symbol suffix.
# Checked in order; first match wins.
_FORM_KEYWORDS: list[tuple[str, str]] = [
    # Mega forms — in this ROM all megas are SPECIES_MEGA_* prefix, not suffix.
    # Prefix check is handled explicitly in detect_form_type().
    # Keeping these as a safeguard for any suffix-style edge cases.
    ("_MEGA_",       "mega"),
    # Gigantamax
    ("_GMAX",        "gmax"),
    # Primal
    ("_PRIMAL",      "primal"),
    # Regional
    ("_ALOLAN",      "regional"),
    ("_GALARIAN",    "regional"),
    ("_HISUIAN",     "regional"),
    ("_PALDEAN",     "regional"),
    # Totem
    ("_TOTEM",       "totem"),
    # Battle-only forms (Aegislash, Wishiwashi, etc.)
    ("_BLADE",       "battle_form"),
    ("_SCHOOL",      "battle_form"),
    # Alternate/special forms – order matters less from here
    ("_ORIGIN",      "alt_form"),
    ("_SKY",         "alt_form"),
    ("_THERIAN",     "alt_form"),
    ("_PIROUETTE",   "alt_form"),
    ("_RESOLUTE",    "alt_form"),
    ("_UNBOUND",     "alt_form"),
    ("_ULTRA",       "alt_form"),
    ("_DUSK_MANE",   "alt_form"),
    ("_DAWN_WINGS",  "alt_form"),
    ("_COMPLETE",    "alt_form"),
    ("_10",          "alt_form"),
    ("_CORE",        "alt_form"),
    ("_WHITE",       "alt_form"),
    ("_BLACK",       "alt_form"),
    ("_SHADOW",      "alt_form"),
    ("_INCARNATE",   "alt_form"),
    ("_ATTACK",      "alt_form"),
    ("_DEFENSE",     "alt_form"),
    ("_SPEED",       "alt_form"),
    # Rotom appliance forms — must match only SPECIES_ROTOM_* to avoid
    # false positives (e.g. _HEAT would match SPECIES_HEATRAN).
    # Handled explicitly in detect_form_type() via startswith check.
    # Cosmetic / gender / colour forms
    ("_FEMALE",      "cosmetic_form"),
    ("_MALE",        "cosmetic_form"),
    ("_AUTUMN",      "cosmetic_form"),
    ("_SUMMER",      "cosmetic_form"),
    ("_SPRING",      "cosmetic_form"),
    ("_WINTER",      "cosmetic_form"),
    ("_RED_STRIPED", "cosmetic_form"),
    ("_BLUE_STRIPED","cosmetic_form"),
    ("_SANDY",       "cosmetic_form"),
    ("_TRASHY",      "cosmetic_form"),
    # Drives / Kyurem fusions / Calyrex fusions
    ("_BURN",        "alt_form"),
    ("_CHILL",       "alt_form"),
    ("_DOUSE",       "alt_form"),
    ("_SHOCK",       "alt_form"),
    # Deoxys handled above by _ATTACK/_DEFENSE/_SPEED
    # Misc special state forms
    ("_TERASTAL",    "alt_form"),
    ("_LIMITED",     "alt_form"),
    ("_SPRINTING",   "alt_form"),
    ("_SWIMMING",    "alt_form"),
    ("_GLIDING",     "alt_form"),
    ("_DRIVE",       "alt_form"),
    ("_AQUATIC",     "alt_form"),
    ("_GLIDE",       "alt_form"),
    ("_LOW_POWER",   "alt_form"),
    ("_COMBAT",      "alt_form"),
    ("_BLAZE",       "alt_form"),
    ("_AQUA",        "alt_form"),
    ("_MASTERPIECE", "alt_form"),
    ("_BLOODMOON",   "alt_form"),
    ("_STELLAR",     "alt_form"),
    ("_WELLSPRING",  "alt_form"),
    ("_HEARTHFLAME", "alt_form"),
    ("_CORNERSTONE", "alt_form"),
    ("_TEAL",        "alt_form"),
    # Revavroom starmobiles
    ("_SEGIN",       "alt_form"),
    ("_SCHEDAR",     "alt_form"),
    ("_NAVI",        "alt_form"),
    ("_RUCHBAH",     "alt_form"),
    ("_CAPH",        "alt_form"),
    # Oinkologne gender form
    ("_OINKOLOGNE",  "cosmetic_form"),  # handled by _FEMALE above usually
]

# Known base species that also appear with a recognised suffix but are the
# base form (e.g. SPECIES_ROTOM is not a form of anything).
_NOT_A_FORM: frozenset[str] = frozenset({
    "SPECIES_ROTOM",       # Rotom base form
    "SPECIES_WORMADAM",    # Wormadam plant cloak (base)
    "SPECIES_GIRATINA",    # Giratina Altered (base)
    "SPECIES_SHAYMIN",     # Shaymin Land (base)
    "SPECIES_DEOXYS",      # Deoxys Normal (base)
    "SPECIES_KELDEO",      # Keldeo Ordinary (base)
    "SPECIES_MELOETTA",    # Meloetta Aria (base)
    "SPECIES_HOOPA",       # Hoopa Confined (base)
    "SPECIES_ZYGARDE",     # Zygarde 50% (base)
    "SPECIES_NECROZMA",    # Necrozma base
    "SPECIES_CALYREX",     # Calyrex base
    "SPECIES_OGERPON",     # Ogerpon Teal Mask (base)
    "SPECIES_KORAIDON",    # Koraidon Apex Build (base)
    "SPECIES_MIRAIDON",    # Miraidon Ultimate Mode (base)
    "SPECIES_TERAPAGOS",   # Terapagos Normal (base)
    "SPECIES_URSHIFU",     # Urshifu Single Strike (base)
    "SPECIES_TORNADUS",    # Tornadus Incarnate (base)
    "SPECIES_THUNDURUS",   # Thundurus Incarnate (base)
    "SPECIES_LANDORUS",    # Landorus Incarnate (base)
    "SPECIES_ENAMORUS",    # Enamorus Incarnate (base)
})


def detect_form_type(species_symbol: str, display_name: str) -> str:
    """
    Classify a species symbol into a form_type string.

    Returns one of:
      "base"           – normal/base species, directly assignable
      "regional"       – regional variant (Alolan, Galarian, Hisuian, Paldean)
      "mega"           – Mega Evolution, never assign directly
      "gmax"           – Gigantamax form, never assign directly
      "primal"         – Primal reversion, never assign directly
      "battle_form"    – battle-only transient form
      "totem"          – Totem form
      "cosmetic_form"  – cosmetic/gender/season variant
      "alt_form"       – other named alternate form
      "stub_form"      – has "-----" name and unrecognised suffix → treat as form
    """
    if species_symbol == "SPECIES_NONE":
        return "none"

    if species_symbol in _NOT_A_FORM:
        return "base"

    sym = species_symbol  # already uppercase

    # Mega forms in this ROM use SPECIES_MEGA_* prefix
    if sym.startswith("SPECIES_MEGA_"):
        return "mega"

    # Rotom appliance forms: SPECIES_ROTOM_HEAT/WASH/FROST/FAN/MOW
    # Checked by prefix to avoid matching SPECIES_HEATRAN etc.
    _ROTOM_APPLIANCES = ("_HEAT", "_WASH", "_FROST", "_FAN", "_MOW")
    if sym.startswith("SPECIES_ROTOM_") and any(sym.endswith(s) for s in _ROTOM_APPLIANCES):
        return "alt_form"

    for keyword, form_type in _FORM_KEYWORDS:
        if keyword in sym:
            return form_type

    # Stub with no recognised keyword → still treat as alt form
    if display_name == "-----":
        return "stub_form"

    return "base"


def base_form_group(species_symbol: str) -> str:
    """
    Return a normalised base-form group key for grouping form families.
    Strips known form suffixes so that SPECIES_CHARIZARD_MEGA_X,
    SPECIES_CHARIZARD_MEGA_Y, and SPECIES_CHARIZARD all map to
    'SPECIES_CHARIZARD'.

    This is best-effort for the first pass. The output column is useful
    for grouping but may need manual overrides for edge cases.
    """
    sym = species_symbol

    # Prefix-mega: SPECIES_MEGA_VENUSAUR → SPECIES_VENUSAUR
    if sym.startswith("SPECIES_MEGA_"):
        # Remove suffix like _X, _Y for charizard/mewtwo megas
        base = sym[len("SPECIES_MEGA_"):]
        base = base.removesuffix("_X").removesuffix("_Y")
        return f"SPECIES_{base}"

    # Strip longest-matching keyword suffixes
    for keyword, _ in _FORM_KEYWORDS:
        idx = sym.find(keyword)
        if idx != -1:
            return sym[:idx]

    return sym


# ── Mono-type specialist table ──────────────────────────────────────────────
# Maps trainer class constant → specialty type string.
# Champion is intentionally excluded per spec.

MONO_TYPE_BY_CLASS: dict[str, str] = {
    # Johto Gym Leaders
    "TRAINERCLASS_LEADER_FALKNER": "FLYING",
    "TRAINERCLASS_LEADER_BUGSY":   "BUG",
    "TRAINERCLASS_LEADER_WHITNEY": "NORMAL",
    "TRAINERCLASS_LEADER_MORTY":   "GHOST",
    "TRAINERCLASS_LEADER_CHUCK":   "FIGHTING",
    "TRAINERCLASS_LEADER_JASMINE": "STEEL",
    "TRAINERCLASS_LEADER_PRYCE":   "ICE",
    "TRAINERCLASS_LEADER_CLAIR":   "DRAGON",
    # Kanto Gym Leaders
    "TRAINERCLASS_LEADER_BROCK":    "ROCK",
    "TRAINERCLASS_LEADER_MISTY":    "WATER",
    "TRAINERCLASS_LEADER_LT_SURGE": "ELECTRIC",
    "TRAINERCLASS_LEADER_ERIKA":    "GRASS",
    "TRAINERCLASS_LEADER_JANINE":   "POISON",
    "TRAINERCLASS_LEADER_SABRINA":  "PSYCHIC",
    "TRAINERCLASS_LEADER_BLAINE":   "FIRE",
    # TRAINERCLASS_LEADER_BLUE intentionally omitted (mixed team)
    # Elite Four
    "TRAINERCLASS_ELITE_FOUR_WILL":  "PSYCHIC",
    "TRAINERCLASS_ELITE_FOUR_KOGA":  "POISON",
    "TRAINERCLASS_ELITE_FOUR_BRUNO": "FIGHTING",
    "TRAINERCLASS_ELITE_FOUR_KAREN": "DARK",
    # TRAINERCLASS_CHAMPION intentionally omitted per spec
}

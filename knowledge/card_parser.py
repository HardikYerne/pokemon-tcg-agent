import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class Attack:
    name:   str
    cost:   str
    damage: str
    effect: str


@dataclass
class Card:
    card_id:       str
    name:          str
    category:      str       # Pokemon | Trainer | Energy
    subtype:       str       # Basic, Stage1, Stage2, Item, Supporter, Stadium, etc.
    special_tag:   str       # Future, Ancient, Tera, Fossil, Trainer's Pokemon, etc.
    expansion:     str
    collection_no: str
    hp:            Optional[int]
    poke_type:     Optional[str]
    weakness:      Optional[str]
    resistance:    Optional[str]
    retreat:       Optional[int]
    rule_text:     Optional[str]
    prev_stage:    Optional[str]
    attacks:       list = field(default_factory=list)

    def is_pokemon(self):   return self.category == "Pokemon"
    def is_trainer(self):   return self.category == "Trainer"
    def is_energy(self):    return self.category == "Energy"
    def is_basic(self):     return self.subtype  == "Basic"
    def is_stage1(self):    return self.subtype  == "Stage1"
    def is_stage2(self):    return self.subtype  == "Stage2"
    def is_supporter(self): return self.subtype  == "Supporter"
    def is_item(self):      return self.subtype  == "Item"


# ── Stage string → (category, subtype) ─────────────────────────────────────
STAGE_MAP = {
    "Basic Pokémon":    ("Pokemon",  "Basic"),
    "Stage 1 Pokémon":  ("Pokemon",  "Stage1"),
    "Stage 2 Pokémon":  ("Pokemon",  "Stage2"),
    "Basic Energy":     ("Energy",   "Basic"),
    "Special Energy":   ("Energy",   "Special"),
    "Item":             ("Trainer",  "Item"),
    "Supporter":        ("Trainer",  "Supporter"),
    "Stadium":          ("Trainer",  "Stadium"),
    "Pokémon Tool":     ("Trainer",  "Tool"),
}

def infer_category_subtype(stage_val, category_val):
    """Infer (category, subtype) from Stage and Category columns."""
    stage = str(stage_val).strip() if stage_val and str(stage_val) != "nan" else ""
    cat   = str(category_val).strip() if category_val and str(category_val) != "nan" else ""

    if stage in STAGE_MAP:
        return STAGE_MAP[stage]

    # fallback — check partial matches
    if "Pokémon" in stage:  return ("Pokemon", stage.replace(" Pokémon","").strip())
    if "Energy"  in stage:  return ("Energy",  stage)
    if stage in ("Item","Supporter","Stadium","Pokémon Tool"): return ("Trainer", stage)

    # Fossil, Technical Machine → Trainer/Item
    if cat in ("Fossil", "Technical Machine"): return ("Trainer", cat)

    return ("Unknown", stage or cat or "Unknown")


def load_cards(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path, encoding="utf-8")
    print(f"[card_parser] Loaded {len(df)} rows")

    def safe(val, default=None):
        try:
            if pd.isna(val): return default
        except Exception: pass
        return val

    def safe_int(val):
        try:
            return int(val) if not pd.isna(val) else None
        except (ValueError, TypeError):
            return None

    cards = {}
    for _, row in df.iterrows():
        card_id = str(safe(row.get("Card ID"), "")).strip()
        if not card_id:
            continue

        stage_raw    = safe(row.get("Stage (Pokémon)/Type (Energy and Trainer)"))
        category_raw = safe(row.get("Category"))
        category, subtype = infer_category_subtype(stage_raw, category_raw)

        # special tag — Future, Ancient, Tera, Trainer's Pokemon, etc.
        special_tag = str(category_raw).strip() if category_raw else ""

        # attack
        attack = None
        move = safe(row.get("Move Name"))
        if move:
            attack = Attack(
                name   = str(move).strip(),
                cost   = str(safe(row.get("Cost"),               "")).strip(),
                damage = str(safe(row.get("Damage"),             "")).strip(),
                effect = str(safe(row.get("Effect Explanation"), "")).strip(),
            )

        card = Card(
            card_id       = card_id,
            name          = str(safe(row.get("Card Name"), "Unknown")).strip(),
            category      = category,
            subtype       = subtype,
            special_tag   = special_tag,
            expansion     = str(safe(row.get("Expansion"),       "")).strip(),
            collection_no = str(safe(row.get("Collection No."),  "")).strip(),
            hp            = safe_int(row.get("HP")),
            poke_type     = safe(row.get("Type")),
            weakness      = safe(row.get("Weakness")),
            resistance    = safe(row.get("Resistance (Type)")),
            retreat       = safe_int(row.get("Retreat")),
            rule_text     = safe(row.get("Rule")),
            prev_stage    = safe(row.get("Previous stage")),
            attacks       = [attack] if attack else [],
        )
        cards[card_id] = card

    print(f"[card_parser] Parsed {len(cards)} valid cards")
    return cards


def summary(cards: dict):
    pokemon  = sum(1 for c in cards.values() if c.is_pokemon())
    trainers = sum(1 for c in cards.values() if c.is_trainer())
    energy   = sum(1 for c in cards.values() if c.is_energy())
    with_atk = sum(1 for c in cards.values() if c.attacks)
    unknown  = sum(1 for c in cards.values() if c.category == "Unknown")

    # subtypes
    basics   = sum(1 for c in cards.values() if c.is_basic()     and c.is_pokemon())
    stage1   = sum(1 for c in cards.values() if c.is_stage1())
    stage2   = sum(1 for c in cards.values() if c.is_stage2())

    # special tags
    tags = {}
    for c in cards.values():
        if c.special_tag:
            tags[c.special_tag] = tags.get(c.special_tag, 0) + 1

    types = sorted({str(c.poke_type) for c in cards.values()
                    if c.poke_type and c.is_pokemon()})

    print(f"\n── Card pool summary ───────────────────────")
    print(f"  Total          : {len(cards)}")
    print(f"  Pokémon        : {pokemon}  (Basic:{basics} S1:{stage1} S2:{stage2})")
    print(f"  Trainers       : {trainers}")
    print(f"  Energy         : {energy}")
    print(f"  With attack    : {with_atk}")
    print(f"  Unknown        : {unknown}")
    print(f"  Types          : {', '.join(types)}")
    print(f"\n── Special tags ────────────────────────────")
    for tag, count in sorted(tags.items(), key=lambda x: -x[1]):
        print(f"  {tag:40} : {count}")
    print(f"────────────────────────────────────────────\n")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import CSV_EN

    cards = load_cards(CSV_EN)
    summary(cards)

    print("── Sample Pokémon ──────────────────────────")
    shown = 0
    for card in cards.values():
        if card.is_pokemon():
            atk = card.attacks[0] if card.attacks else None
            print(f"  {card.card_id:6} | {card.name:22} | "
                  f"HP:{str(card.hp):4} | {str(card.poke_type):6} | "
                  f"{card.subtype:8} | {card.special_tag:15} | "
                  f"Atk:{atk.name if atk else 'none'}")
            shown += 1
        if shown >= 5:
            break

    print("\n── Sample Trainers ─────────────────────────")
    shown = 0
    for card in cards.values():
        if card.is_trainer():
            print(f"  {card.card_id:6} | {card.name:22} | {card.subtype:12}")
            shown += 1
        if shown >= 5:
            break
    print("────────────────────────────────────────────")
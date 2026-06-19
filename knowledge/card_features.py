import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class CardFeatures:
    card_id:            str
    name:               str
    category:           str
    subtype:            str
    special_tag:        str
    expansion:          str
    hp:                 Optional[int]
    poke_type:          Optional[str]
    weakness:           Optional[str]
    resistance:         Optional[str]
    retreat:            Optional[int]
    has_ability:        bool
    has_attack:         bool
    attack_name:        Optional[str]
    attack_damage:      Optional[int]    # numeric damage value
    attack_cost:        Optional[int]    # number of energy needed
    damage_per_energy:  Optional[float] # efficiency ratio
    ko_threshold:       Optional[int]   # max HP this card can 1HKO
    image_path:         Optional[str]

    # strategic tags
    is_ex:              bool   # ex cards give 2 prizes when KO'd
    is_v:               bool   # V cards also give 2 prizes
    is_vmax:            bool
    is_gx:              bool
    prize_value:        int    # how many prizes opponent gets for KO

    # deck building tags
    is_draw_supporter:  bool   # draws cards
    is_search_card:     bool   # searches deck
    is_energy_accel:    bool   # attaches extra energy
    is_disruption:      bool   # disrupts opponent


# ── Damage parsing ────────────────────────────────────────────────────────────

def parse_damage(damage_str: str) -> Optional[int]:
    """Parse damage string → int. Handles '120', '120+', '120x', '-'"""
    if not damage_str or damage_str in ("-", "", "None", "nan"):
        return None
    # extract first number
    match = re.search(r"\d+", str(damage_str))
    return int(match.group()) if match else None


def parse_energy_cost(cost_str: str) -> Optional[int]:
    """
    Parse energy cost string → count.
    Cost is stored as symbols e.g. '{R}{R}{C}' = 3 energy
    or as a number string '3'
    """
    if not cost_str or cost_str in ("", "None", "nan"):
        return None
    s = str(cost_str)
    # count energy symbols like {R}, {G}, {C} etc.
    symbols = re.findall(r"\{[A-Z]\}", s)
    if symbols:
        return len(symbols)
    # try plain number
    match = re.search(r"\d+", s)
    return int(match.group()) if match else None


# ── Name-based flags ──────────────────────────────────────────────────────────

def detect_flags(name: str, rule_text: str, category: str, subtype: str):
    """Detect strategic flags from card name and rule text."""
    n = name.lower()
    r = (rule_text or "").lower()

    is_ex   = " ex"   in n or n.endswith(" ex")
    is_v    = " v"    in n and " vmax" not in n and " vstar" not in n
    is_vmax = "vmax"  in n
    is_gx   = " gx"  in n

    # prize value
    if is_vmax:
        prize_value = 3
    elif is_ex or is_v or is_gx:
        prize_value = 2
    else:
        prize_value = 1

    # trainer card strategic roles
    is_draw_supporter = (
        category == "Trainer" and subtype == "Supporter" and
        any(kw in r for kw in ["draw", "hand", "look at"])
    )
    is_search_card = any(kw in r for kw in
                         ["search", "deck", "put into your hand"])
    is_energy_accel = any(kw in r for kw in
                          ["attach", "energy", "from your deck"])
    is_disruption = any(kw in r for kw in
                        ["discard", "opponent", "shuffle", "lost zone"])

    return {
        "is_ex":             is_ex,
        "is_v":              is_v,
        "is_vmax":           is_vmax,
        "is_gx":             is_gx,
        "prize_value":       prize_value,
        "is_draw_supporter": is_draw_supporter,
        "is_search_card":    is_search_card,
        "is_energy_accel":   is_energy_accel,
        "is_disruption":     is_disruption,
    }


# ── Main builder ──────────────────────────────────────────────────────────────

def build_features(cards: dict, pdf_index: dict) -> dict[str, CardFeatures]:
    """
    Merge CSV card data + PDF index → CardFeatures dict.
    cards     : {card_id: Card}      from card_parser.py
    pdf_index : {card_id: dict}      from pdf_extractor.py
    """
    features = {}

    for card_id, card in cards.items():
        # get PDF info (image path)
        pdf_info   = pdf_index.get(card_id, {})
        image_path = pdf_info.get("image_path")

        # attack info
        atk          = card.attacks[0] if card.attacks else None
        dmg_raw      = atk.damage if atk else None
        cost_raw     = atk.cost   if atk else None
        attack_name  = atk.name   if atk else None
        attack_dmg   = parse_damage(dmg_raw)
        attack_cost  = parse_energy_cost(cost_raw)

        # damage per energy
        dpe = None
        if attack_dmg is not None and attack_cost and attack_cost > 0:
            dpe = round(attack_dmg / attack_cost, 2)

        # KO threshold — max HP this card can one-shot
        ko_threshold = attack_dmg  # base damage

        # has_ability — rule text often contains ability descriptions
        rule = card.rule_text or ""
        has_ability = any(kw in rule.lower() for kw in
                         ["ability", "once during your turn", "when you play"])

        # flags
        flags = detect_flags(
            card.name,
            card.rule_text,
            card.category,
            card.subtype,
        )

        cf = CardFeatures(
            card_id           = card_id,
            name              = card.name,
            category          = card.category,
            subtype           = card.subtype,
            special_tag       = card.special_tag,
            expansion         = card.expansion,
            hp                = card.hp,
            poke_type         = str(card.poke_type) if card.poke_type else None,
            weakness          = str(card.weakness)  if card.weakness  else None,
            resistance        = str(card.resistance) if card.resistance else None,
            retreat           = card.retreat,
            has_ability       = has_ability,
            has_attack        = atk is not None,
            attack_name       = attack_name,
            attack_damage     = attack_dmg,
            attack_cost       = attack_cost,
            damage_per_energy = dpe,
            ko_threshold      = ko_threshold,
            image_path        = image_path,
            **flags,
        )
        features[card_id] = cf

    print(f"[card_features] Built features for {len(features)} cards")
    return features


def save_features(features: dict, output_path: Path):
    """Save all CardFeatures to JSON."""
    data = {k: asdict(v) for k, v in features.items()}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[card_features] Saved to {output_path}")


def summary(features: dict):
    pokemon   = [f for f in features.values() if f.category == "Pokemon"]
    trainers  = [f for f in features.values() if f.category == "Trainer"]
    energy    = [f for f in features.values() if f.category == "Energy"]
    ex_cards  = [f for f in pokemon if f.is_ex]
    with_dpe  = [f for f in pokemon if f.damage_per_energy]

    avg_dpe   = (sum(f.damage_per_energy for f in with_dpe)
                 / len(with_dpe)) if with_dpe else 0
    top_dpe   = sorted(with_dpe, key=lambda f: f.damage_per_energy, reverse=True)[:5]
    draw_sups = [f for f in trainers if f.is_draw_supporter]
    searchers = [f for f in features.values() if f.is_search_card]

    print(f"\n── Card features summary ───────────────────")
    print(f"  Total          : {len(features)}")
    print(f"  Pokémon        : {len(pokemon)}")
    print(f"  Trainers       : {len(trainers)}")
    print(f"  Energy         : {len(energy)}")
    print(f"  ex cards       : {len(ex_cards)}  (give 2 prizes)")
    print(f"  Draw supporters: {len(draw_sups)}")
    print(f"  Search cards   : {len(searchers)}")
    print(f"  Avg dmg/energy : {avg_dpe:.1f}")
    print(f"\n── Top damage/energy efficiency ────────────")
    for f in top_dpe:
        print(f"  {f.name:25} | {f.attack_damage:4}dmg / "
              f"{f.attack_cost}e = {f.damage_per_energy:.1f}")
    print(f"────────────────────────────────────────────\n")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from config import CSV_EN, KNOW_DIR
    from knowledge.card_parser import load_cards

    # load CSV cards
    cards = load_cards(CSV_EN)

    # load PDF index
    pdf_index_path = KNOW_DIR / "pdf_card_index.json"
    if pdf_index_path.exists():
        with open(pdf_index_path, encoding="utf-8") as f:
            pdf_index = json.load(f)
        print(f"[card_features] Loaded PDF index: {len(pdf_index)} entries")
    else:
        print("[card_features] No PDF index found — skipping image paths")
        pdf_index = {}

    # build features
    features = build_features(cards, pdf_index)

    # summary
    summary(features)

    # save
    out = KNOW_DIR / "card_knowledge_base.json"
    save_features(features, out)

    print("\n── Sample Pokémon features ─────────────────")
    shown = 0
    for f in features.values():
        if f.category == "Pokemon" and f.has_attack:
            print(f"  {f.card_id:6} | {f.name:22} | "
                  f"HP:{str(f.hp):4} | {str(f.poke_type):6} | "
                  f"Atk:{str(f.attack_damage):4} | "
                  f"Cost:{str(f.attack_cost):2} | "
                  f"DPE:{str(f.damage_per_energy):5} | "
                  f"Prize:{f.prize_value} | "
                  f"img:{'yes' if f.image_path else 'no'}")
            shown += 1
        if shown >= 5:
            break
    print("────────────────────────────────────────────")
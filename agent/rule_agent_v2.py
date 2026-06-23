import sys
import json
import random
from pathlib import Path

import os
KAGGLE_PATH = Path("/kaggle_simulations/agent")
LOCAL_PATH  = Path(os.getcwd())
ROOT        = KAGGLE_PATH if KAGGLE_PATH.exists() else LOCAL_PATH
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sample_submission"))
sys.path.insert(0, "/kaggle_simulations/agent")

from cg.api import to_observation_class

# ── Option types ──────────────────────────────────────────────────────────────
T_MULLIGAN       = 0
T_COIN_HEAD      = 1
T_COIN_TAIL      = 2
T_SELECT_POKEMON = 3
T_PLAY_CARD      = 7
T_PLACE_BENCH    = 8
T_EVOLVE         = 9
T_USE_ABILITY    = 12
T_ATTACK         = 13
T_END_TURN       = 14

OPTION_TYPE = {
    0:"MULLIGAN", 1:"COIN_HEAD", 2:"COIN_TAIL",
    3:"SELECT_POKEMON", 7:"PLAY_CARD", 8:"PLACE_BENCH",
    9:"EVOLVE", 12:"USE_ABILITY", 13:"ATTACK", 14:"END_TURN"
}


class RuleAgent:
    """
    V2 Rule Agent — improved attack selection and energy awareness.

    Key improvements over V1:
    1. Counts energy on active Pokemon before committing to attack
    2. Prefers high-damage attacks that KO opponent
    3. Uses Spike Draw (type 7, low damage) early to draw cards
    4. Aggressive prize racing — always attack if we can deal damage
    5. Smarter going-second detection and response
    """

    def __init__(self, deck: list, card_features: dict = None,
                 attacks_db: dict = None, verbose: bool = False):
        self.deck          = deck
        self.card_features = card_features or {}
        self.attacks_db    = attacks_db or {}   # attackId -> attack data
        self.verbose       = verbose
        self.turn_count    = 0

    # ── Main entry point ──────────────────────────────────────────────────────

    def act(self, obs_dict: dict) -> list:
        obs = to_observation_class(obs_dict)

        # deck selection
        if obs.select is None:
            return self.deck

        options  = obs.select.option
        n        = len(options)
        minCount = obs.select.minCount
        maxCount = obs.select.maxCount

        if n == 0:
            return []

        types = [o.type for o in options]

        # coin flip — always heads
        if T_COIN_HEAD in types:
            return self._pick_type(options, T_COIN_HEAD)

        # mulligan
        if T_MULLIGAN in types:
            return self._random_of_type(options, T_MULLIGAN, minCount)

        # pokemon selection
        if all(t == T_SELECT_POKEMON for t in types):
            return self._select_pokemon(options, minCount, obs_dict)

        # main turn
        action = self._main_turn(options, minCount, maxCount, obs_dict)
        self.turn_count += 1
        return action

    # ── Main turn ─────────────────────────────────────────────────────────────

    def _main_turn(self, options, minCount, maxCount, obs_dict) -> list:
        types   = [o.type for o in options]
        current = obs_dict.get("current", {})
        players = current.get("players", [{}, {}])
        my_idx  = current.get("yourIndex", 0)
        me      = players[my_idx] if len(players) > my_idx else {}
        opp     = players[1-my_idx] if len(players) > 1-my_idx else {}

        my_active   = me.get("active", [])
        opp_active  = opp.get("active", [])
        my_energy   = len(my_active[0].get("energies", [])) if my_active else 0
        opp_hp      = opp_active[0]["hp"] if opp_active else 9999
        my_prizes   = sum(1 for p in me.get("prize",[]) if p is None)
        opp_prizes  = sum(1 for p in opp.get("prize",[]) if p is None)
        prize_lead  = my_prizes - opp_prizes
        turn        = current.get("turn", 0)
        first_player = current.get("firstPlayer", 0)
        going_second = (my_idx != first_player)

        if self.verbose:
            print(f"  [v2] turn={turn} energy={my_energy} "
                  f"opp_hp={opp_hp} prizes={my_prizes}-{opp_prizes} "
                  f"P2={going_second}")

        # ── 1. ATTACK — always if KO available ───────────────────────────────
        if T_ATTACK in types:
            atk_indices = [i for i,o in enumerate(options) if o.type == T_ATTACK]
            ko_idx = self._find_ko_attack(atk_indices, options, opp_hp)
            if ko_idx is not None:
                if self.verbose: print(f"  [v2] → KO ATTACK")
                return [ko_idx]

        # ── 2. BENCH — build board if bench is empty ─────────────────────────
        my_bench = len(me.get("bench", []))
        if T_PLACE_BENCH in types and my_bench == 0:
            bench_idx = [i for i,o in enumerate(options) if o.type == T_PLACE_BENCH]
            if bench_idx:
                best = self._best_bench(bench_idx, options)
                if self.verbose: print(f"  [v2] → BENCH (empty bench)")
                return [best]

        # ── 3. EVOLVE ─────────────────────────────────────────────────────────
        if T_EVOLVE in types:
            evo_idx = [i for i,o in enumerate(options) if o.type == T_EVOLVE]
            if evo_idx:
                if self.verbose: print(f"  [v2] → EVOLVE")
                return [evo_idx[0]]

        # ── 4. PLAY CARD — supporter/item ────────────────────────────────────
        if T_PLAY_CARD in types:
            card_idx = [i for i,o in enumerate(options) if o.type == T_PLAY_CARD]
            if card_idx:
                best = self._best_card(card_idx, options, current)
                if self.verbose: print(f"  [v2] → PLAY_CARD")
                return [best]

        # ── 5. ATTACK — best available even without KO ────────────────────────
        if T_ATTACK in types:
            atk_indices = [i for i,o in enumerate(options) if o.type == T_ATTACK]
            # going second — always attack aggressively
            if going_second or my_energy >= 2:
                best = self._best_attack(atk_indices, options, opp_hp)
                if best is not None:
                    if self.verbose: print(f"  [v2] → ATTACK (aggressive)")
                    return [best]

        # ── 6. BENCH — build board ────────────────────────────────────────────
        if T_PLACE_BENCH in types:
            bench_idx = [i for i,o in enumerate(options) if o.type == T_PLACE_BENCH]
            if bench_idx:
                best = self._best_bench(bench_idx, options)
                if self.verbose: print(f"  [v2] → BENCH")
                return [best]

        # ── 7. USE ABILITY ────────────────────────────────────────────────────
        if T_USE_ABILITY in types:
            ab_idx = [i for i,o in enumerate(options) if o.type == T_USE_ABILITY]
            if ab_idx:
                if self.verbose: print(f"  [v2] → ABILITY")
                return [ab_idx[0]]

        # ── 8. ATTACK — last resort ───────────────────────────────────────────
        if T_ATTACK in types:
            atk_indices = [i for i,o in enumerate(options) if o.type == T_ATTACK]
            best = self._best_attack(atk_indices, options, opp_hp)
            if best is not None:
                if self.verbose: print(f"  [v2] → ATTACK (last resort)")
                return [best]

        # ── 9. END TURN ───────────────────────────────────────────────────────
        if T_END_TURN in types:
            end_idx = next(i for i,o in enumerate(options) if o.type == T_END_TURN)
            if self.verbose: print(f"  [v2] → END_TURN")
            return [end_idx]

        # fallback
        if minCount == 0: return []
        return random.sample(list(range(len(options))), min(minCount, len(options)))

    # ── Attack helpers ────────────────────────────────────────────────────────

    def _find_ko_attack(self, atk_indices, options, opp_hp) -> int:
        """Return index of attack that KOs opponent, or None."""
        for i in atk_indices:
            dmg = self._get_damage(options[i].attackId)
            if dmg >= opp_hp:
                return i
        return None

    def _best_attack(self, atk_indices, options, opp_hp) -> int:
        """Return index of highest-damage attack."""
        best_idx   = None
        best_score = -1
        for i in atk_indices:
            dmg = self._get_damage(options[i].attackId)
            score = dmg + (10000 if dmg >= opp_hp else 0)
            if score > best_score:
                best_score = score
                best_idx   = i
        return best_idx

    def _get_damage(self, attack_id) -> int:
        """Look up damage from attacks_db or card_features."""
        if not attack_id:
            return 0
        # check attacks db first (most accurate)
        atk = self.attacks_db.get(attack_id)
        if atk:
            return atk.get("damage", 0)
        # fallback to card features
        cf = self.card_features.get(str(attack_id))
        if cf:
            return cf.get("attack_damage") or 0
        return 30

    # ── Bench helpers ─────────────────────────────────────────────────────────

    def _best_bench(self, bench_indices, options) -> int:
        """Prefer highest HP bench Pokémon."""
        best_idx   = bench_indices[0]
        best_score = -1
        for i in bench_indices:
            opt    = options[i]
            card_id = getattr(opt, "cardId", None) or getattr(opt, "index", None)
            cf     = self.card_features.get(str(card_id)) if card_id else None
            score  = (cf.get("hp") or 0) if cf else 0
            if score > best_score:
                best_score = score
                best_idx   = i
        return best_idx

    # ── Card play helpers ─────────────────────────────────────────────────────

    def _best_card(self, card_indices, options, current) -> int:
        """Priority: draw supporters > search > energy accel > other."""
        supporter_played = current.get("supporterPlayed", False)
        best_idx   = card_indices[0]
        best_score = -1
        for i in card_indices:
            opt     = options[i]
            card_id = getattr(opt, "cardId", None) or getattr(opt, "index", None)
            cf      = self.card_features.get(str(card_id)) if card_id else None
            score   = 10
            if cf:
                if cf.get("subtype") == "Supporter" and supporter_played:
                    score = -1
                elif cf.get("is_draw_supporter"):
                    score = 100
                elif cf.get("is_search_card"):
                    score = 80
                elif cf.get("is_energy_accel"):
                    score = 70
                elif cf.get("is_disruption"):
                    score = 50
            if score > best_score:
                best_score = score
                best_idx   = i
        return best_idx

    # ── Pokemon selection ─────────────────────────────────────────────────────

    def _select_pokemon(self, options, minCount, obs_dict) -> list:
        scored = []
        for i, opt in enumerate(options):
            card_id = getattr(opt, "cardId", None)
            area    = getattr(opt, "area", None)
            cf      = self.card_features.get(str(card_id)) if card_id else None
            hp      = (cf.get("hp") or 100) if cf else 100
            # area 6 = opponent field (prize target) → prefer low HP
            score   = -hp if area == 6 else hp
            scored.append((score, i))
        scored.sort(reverse=True)
        count  = max(minCount, 1) if minCount > 0 else 1
        count  = min(count, len(options))
        return [idx for _, idx in scored[:count]]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pick_type(self, options, target_type) -> list:
        for i, o in enumerate(options):
            if o.type == target_type:
                return [i]
        return [0]

    def _random_of_type(self, options, target_type, minCount) -> list:
        indices = [i for i, o in enumerate(options) if o.type == target_type]
        if not indices:
            indices = list(range(len(options)))
        count = max(minCount, 1)
        return random.sample(indices, min(count, len(indices)))


# ── Factory ───────────────────────────────────────────────────────────────────

def make_agent(deck: list, card_features: dict = None, attacks_db: dict = None):
    """Returns agent function for Kaggle submission."""
    bot = RuleAgent(deck, card_features, attacks_db)
    def agent(obs_dict: dict) -> list:
        return bot.act(obs_dict)
    return agent


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random as rnd
    from cg.sim import lib
    from environment.simulator_wrapper import load_deck_csv, run_game

    deck = load_deck_csv(ROOT / "deck.csv")

    with open(ROOT / "knowledge" / "card_knowledge_base.json", encoding="utf-8") as f:
        features = json.load(f)

    # load attacks db
    attacks_data = json.loads(lib.AllAttack().decode())
    atk_db = {a["attackId"]: a for a in attacks_data}
    print(f"[v2] Loaded {len(atk_db)} attacks")

    agent_v2 = make_agent(deck, features, atk_db)

    def random_agent(obs_dict):
        obs = to_observation_class(obs_dict)
        if obs.select is None: return deck
        n = len(obs.select.option)
        minCount = obs.select.minCount
        if n == 0: return []
        if minCount == 0: return []
        return rnd.sample(list(range(n)), min(minCount, n))

    print("\n[v2] Rule v2 vs Random — 20 games")
    print("─"*55)
    wins = losses = 0
    for i in range(20):
        if i % 2 == 0:
            r = run_game(deck, deck, agent_v2, random_agent)
            if r["winner"] == 0: wins += 1
            else: losses += 1
            side = "V2=P0"
        else:
            r = run_game(deck, deck, random_agent, agent_v2)
            if r["winner"] == 1: wins += 1
            else: losses += 1
            side = "V2=P1"
        print(f"  Game {i+1:2d} [{side}]: W=P{r['winner']} T={r['turns']:3d}")

    print(f"\n  V2 wins: {wins}/20 ({wins*5}%)")
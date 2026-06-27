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
T_PLACE_HAND     = 6   # play Pokemon from hand to bench
T_PLAY_CARD      = 7   # play trainer card from hand
T_PLACE_BENCH    = 8   # place on bench
T_EVOLVE         = 9
T_USE_ABILITY    = 12
T_ATTACK         = 13
T_END_TURN       = 14

OPTION_TYPE = {
    0:"MULLIGAN", 1:"COIN_HEAD", 2:"COIN_TAIL",
    3:"SELECT_POKEMON", 6:"PLACE_HAND", 7:"PLAY_CARD",
    8:"PLACE_BENCH", 9:"EVOLVE", 12:"USE_ABILITY",
    13:"ATTACK", 14:"END_TURN"
}


class RuleAgent:
    """
    Rule Agent — priority-driven decision engine.

    Decision priority:
    1. Attack if KO available
    2. Evolve Pokemon
    3. Place Pokemon from hand to bench (type 6) — NEW
    4. Place on bench (type 8)
    5. Play trainer cards
    6. Use ability
    7. Best available attack
    8. End turn
    """

    def __init__(self, deck: list, card_features: dict = None,
                 attacks_db: dict = None, verbose: bool = False):
        self.deck          = deck
        self.card_features = card_features or {}
        self.attacks_db    = attacks_db or {}
        self.verbose       = verbose
        self.turn_count    = 0

    def act(self, obs_dict: dict) -> list:
        obs = to_observation_class(obs_dict)

        # deck selection phase
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

        # main turn decisions
        action = self._main_turn(options, minCount, maxCount, obs_dict)
        self.turn_count += 1
        return action

    def _main_turn(self, options, minCount, maxCount, obs_dict) -> list:
        types   = [o.type for o in options]
        current = obs_dict.get("current", {})
        players = current.get("players", [{}, {}])
        my_idx  = current.get("yourIndex", 0)
        me      = players[my_idx]  if len(players) > my_idx  else {}
        opp     = players[1-my_idx] if len(players) > 1-my_idx else {}

        opp_active = opp.get("active", [])
        opp_hp     = opp_active[0]["hp"] if opp_active else 9999
        my_bench   = len(me.get("bench", []))

        # ── 1. ATTACK — KO available ──────────────────────────────────────────
        if T_ATTACK in types:
            atk_idx = [i for i, o in enumerate(options) if o.type == T_ATTACK]
            ko = self._find_ko_attack(atk_idx, options, opp_hp)
            if ko is not None:
                return [ko]

        # ── 2. EVOLVE ─────────────────────────────────────────────────────────
        if T_EVOLVE in types:
            evo = [i for i, o in enumerate(options) if o.type == T_EVOLVE]
            if evo:
                return [evo[0]]

        # ── 3. PLACE POKEMON FROM HAND (type 6) ──────────────────────────────
        if T_PLACE_HAND in types:
            hand_idx = [i for i, o in enumerate(options) if o.type == T_PLACE_HAND]
            if hand_idx:
                return [self._best_bench_pick(hand_idx, options)]

        # ── 4. PLACE ON BENCH (type 8) ────────────────────────────────────────
        if T_PLACE_BENCH in types:
            bench_idx = [i for i, o in enumerate(options) if o.type == T_PLACE_BENCH]
            if bench_idx:
                return [self._best_bench_pick(bench_idx, options)]

        # ── 5. PLAY TRAINER CARD ──────────────────────────────────────────────
        if T_PLAY_CARD in types:
            card_idx = [i for i, o in enumerate(options) if o.type == T_PLAY_CARD]
            if card_idx:
                return [self._best_card(card_idx, options, current)]

        # ── 6. USE ABILITY ────────────────────────────────────────────────────
        if T_USE_ABILITY in types:
            ab = [i for i, o in enumerate(options) if o.type == T_USE_ABILITY]
            if ab:
                return [ab[0]]

        # ── 7. BEST AVAILABLE ATTACK ──────────────────────────────────────────
        if T_ATTACK in types:
            atk_idx = [i for i, o in enumerate(options) if o.type == T_ATTACK]
            best = self._best_attack(atk_idx, options, opp_hp)
            if best is not None:
                return [best]

        # ── 8. END TURN ───────────────────────────────────────────────────────
        if T_END_TURN in types:
            end = next(i for i, o in enumerate(options) if o.type == T_END_TURN)
            return [end]

        # fallback
        if minCount == 0:
            return []
        return random.sample(list(range(len(options))), min(minCount, len(options)))

    # ── Attack helpers ────────────────────────────────────────────────────────

    def _find_ko_attack(self, atk_indices, options, opp_hp):
        for i in atk_indices:
            if self._get_damage(options[i].attackId) >= opp_hp:
                return i
        return None

    def _best_attack(self, atk_indices, options, opp_hp):
        best_idx, best_score = None, -1
        for i in atk_indices:
            dmg   = self._get_damage(options[i].attackId)
            score = dmg + (10000 if dmg >= opp_hp else 0)
            if score > best_score:
                best_score, best_idx = score, i
        return best_idx

    def _get_damage(self, attack_id) -> int:
        if not attack_id:
            return 0
        atk = self.attacks_db.get(attack_id)
        if atk:
            return atk.get("damage", 0)
        cf = self.card_features.get(str(attack_id))
        if cf:
            return cf.get("attack_damage") or 0
        return 30

    # ── Bench helpers ─────────────────────────────────────────────────────────

    def _best_bench_pick(self, indices, options) -> int:
        best_idx, best_score = indices[0], -1
        for i in indices:
            opt     = options[i]
            card_id = getattr(opt, "cardId", None) or getattr(opt, "index", None)
            cf      = self.card_features.get(str(card_id)) if card_id else None
            score   = (cf.get("hp") or 0) if cf else 0
            if score > best_score:
                best_score, best_idx = score, i
        return best_idx

    # ── Card helpers ──────────────────────────────────────────────────────────

    def _best_card(self, card_indices, options, current) -> int:
        supporter_played = current.get("supporterPlayed", False)
        best_idx, best_score = card_indices[0], -1
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
                best_score, best_idx = score, i
        return best_idx

    # ── Pokemon selection ─────────────────────────────────────────────────────

    def _select_pokemon(self, options, minCount, obs_dict) -> list:
        scored = []
        for i, opt in enumerate(options):
            card_id = getattr(opt, "cardId", None)
            area    = getattr(opt, "area", None)
            cf      = self.card_features.get(str(card_id)) if card_id else None
            hp      = (cf.get("hp") or 100) if cf else 100
            score   = -hp if area == 6 else hp
            scored.append((score, i))
        scored.sort(reverse=True)
        count = max(minCount, 1) if minCount > 0 else 1
        count = min(count, len(options))
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
    bot = RuleAgent(deck, card_features, attacks_db)
    def agent(obs_dict: dict) -> list:
        return bot.act(obs_dict)
    return agent


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random as rnd
    from cg.sim import lib
    from environment.simulator_wrapper import load_deck_csv, run_game

    deck     = load_deck_csv(ROOT / "deck.csv")
    with open(ROOT / "knowledge" / "card_knowledge_base.json", encoding="utf-8") as f:
        features = json.load(f)
    atk_db = {a["attackId"]: a for a in json.loads(lib.AllAttack().decode())}

    agent_fn = make_agent(deck, features, atk_db)

    def random_agent(obs_dict):
        obs = to_observation_class(obs_dict)
        if obs.select is None: return deck
        n = len(obs.select.option)
        minCount = obs.select.minCount
        if n == 0: return []
        if minCount == 0: return []
        return rnd.sample(list(range(n)), min(minCount, n))

    print("[rule_agent] Testing — 20 games")
    wins = 0
    for i in range(20):
        if i % 2 == 0:
            r = run_game(deck, deck, agent_fn, random_agent)
            if r["winner"] == 0: wins += 1
        else:
            r = run_game(deck, deck, random_agent, agent_fn)
            if r["winner"] == 1: wins += 1
        print(f"  Game {i+1:2d}: W=P{r['winner']} T={r['turns']:3d}")
    print(f"\nWins: {wins}/20")
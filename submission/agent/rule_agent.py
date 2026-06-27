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
T_PLACE_HAND     = 6
T_PLAY_CARD      = 7
T_PLACE_BENCH    = 8
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
    Final Rule Agent — maximum win rate focused.

    Key strategies:
    1. Going-second: ALWAYS attack first available turn
    2. KO detection with exact damage from simulator DB
    3. Prize race: when behind, attack over everything else
    4. Type 6 handler for bench placement
    5. Highest HP bench preference
    6. Supporter priority for draw engine
    """

    def __init__(self, deck, card_features=None, attacks_db=None, verbose=False):
        self.deck          = deck
        self.card_features = card_features or {}
        self.attacks_db    = attacks_db or {}
        self.verbose       = verbose
        self.turn_count    = 0
        self._game_start   = True
        self._going_second = False

    def act(self, obs_dict: dict) -> list:
        obs = to_observation_class(obs_dict)

        # deck selection
        if obs.select is None:
            return self.deck

        options  = obs.select.option
        n        = len(options)
        minCount = obs.select.minCount

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

        action = self._main_turn(options, minCount, obs_dict)
        self.turn_count += 1
        return action

    def _main_turn(self, options, minCount, obs_dict) -> list:
        types   = [o.type for o in options]
        current = obs_dict.get("current", {})
        players = current.get("players", [{}, {}])
        my_idx  = current.get("yourIndex", 0)
        me      = players[my_idx]  if len(players) > my_idx  else {}
        opp     = players[1-my_idx] if len(players) > 1-my_idx else {}

        # board state
        opp_active   = opp.get("active", [])
        my_active    = me.get("active", [])
        opp_hp       = opp_active[0]["hp"] if opp_active else 9999
        my_hp        = my_active[0]["hp"]  if my_active  else 0
        my_max_hp    = my_active[0].get("maxHp", 1) if my_active else 1
        my_energy    = len(my_active[0].get("energies", [])) if my_active else 0
        my_prizes    = sum(1 for p in me.get("prize",  []) if p is None)
        opp_prizes   = sum(1 for p in opp.get("prize", []) if p is None)
        my_bench     = len(me.get("bench", []))
        turn         = current.get("turn", 0)
        first_player = current.get("firstPlayer", 0)

        # detect going second once
        if self._game_start:
            self._going_second = (my_idx != first_player)
            self._game_start   = False

        # prize race status
        prize_diff   = my_prizes - opp_prizes  # positive = we're winning
        behind       = prize_diff < 0
        hp_pct       = my_hp / my_max_hp if my_max_hp else 1.0
        in_danger    = hp_pct < 0.3  # active pokemon at 30% HP

        if self.verbose:
            print(f"  turn={turn} energy={my_energy} opp_hp={opp_hp} "
                  f"prizes={my_prizes}-{opp_prizes} P2={self._going_second}")

        # ── ATTACK CONDITIONS ─────────────────────────────────────────────────
        if T_ATTACK in types:
            atk_idx = [i for i,o in enumerate(options) if o.type == T_ATTACK]

            # ALWAYS attack if KO available
            ko = self._find_ko(atk_idx, options, opp_hp)
            if ko is not None:
                return [ko]

            # Going second — attack ALWAYS to close tempo gap
            if self._going_second:
                best = self._best_attack(atk_idx, options, opp_hp)
                if best is not None:
                    return [best]

            # Behind on prizes — attack always
            if behind:
                best = self._best_attack(atk_idx, options, opp_hp)
                if best is not None:
                    return [best]

        # ── EVOLVE — strengthen board ─────────────────────────────────────────
        if T_EVOLVE in types:
            evo = [i for i,o in enumerate(options) if o.type == T_EVOLVE]
            if evo:
                return [evo[0]]

        # ── BENCH — build backup ──────────────────────────────────────────────
        if T_PLACE_HAND in types:
            idx = [i for i,o in enumerate(options) if o.type == T_PLACE_HAND]
            if idx and my_bench < 3:
                return [self._best_bench_pick(idx, options)]

        if T_PLACE_BENCH in types:
            idx = [i for i,o in enumerate(options) if o.type == T_PLACE_BENCH]
            if idx and my_bench < 3:
                return [self._best_bench_pick(idx, options)]

        # ── PLAY CARD ─────────────────────────────────────────────────────────
        if T_PLAY_CARD in types:
            idx = [i for i,o in enumerate(options) if o.type == T_PLAY_CARD]
            if idx:
                return [self._best_card(idx, options, current)]

        # ── ABILITY ───────────────────────────────────────────────────────────
        if T_USE_ABILITY in types:
            idx = [i for i,o in enumerate(options) if o.type == T_USE_ABILITY]
            if idx:
                return [idx[0]]

        # ── ATTACK — whenever possible ────────────────────────────────────────
        if T_ATTACK in types:
            atk_idx = [i for i,o in enumerate(options) if o.type == T_ATTACK]
            best = self._best_attack(atk_idx, options, opp_hp)
            if best is not None:
                return [best]

        # ── BENCH — fill up ───────────────────────────────────────────────────
        if T_PLACE_HAND in types:
            idx = [i for i,o in enumerate(options) if o.type == T_PLACE_HAND]
            if idx:
                return [self._best_bench_pick(idx, options)]

        if T_PLACE_BENCH in types:
            idx = [i for i,o in enumerate(options) if o.type == T_PLACE_BENCH]
            if idx:
                return [self._best_bench_pick(idx, options)]

        # ── END TURN ──────────────────────────────────────────────────────────
        if T_END_TURN in types:
            return [next(i for i,o in enumerate(options) if o.type == T_END_TURN)]

        if minCount == 0:
            return []
        return random.sample(list(range(len(options))), min(minCount, len(options)))

    # ── Attack helpers ────────────────────────────────────────────────────────

    def _find_ko(self, atk_idx, options, opp_hp):
        for i in atk_idx:
            if self._dmg(options[i].attackId) >= opp_hp:
                return i
        return None

    def _best_attack(self, atk_idx, options, opp_hp):
        best_i, best_s = None, -1
        for i in atk_idx:
            dmg   = self._dmg(options[i].attackId)
            score = dmg + (10000 if dmg >= opp_hp else 0)
            if score > best_s:
                best_s, best_i = score, i
        return best_i

    def _dmg(self, attack_id) -> int:
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

    def _best_bench_pick(self, indices, options):
        best_i, best_s = indices[0], -1
        for i in indices:
            opt    = options[i]
            cid    = getattr(opt, "cardId", None) or getattr(opt, "index", None)
            cf     = self.card_features.get(str(cid)) if cid else None
            score  = (cf.get("hp") or 0) if cf else 0
            if score > best_s:
                best_s, best_i = score, i
        return best_i

    # ── Card helpers ──────────────────────────────────────────────────────────

    def _best_card(self, indices, options, current):
        sup_played = current.get("supporterPlayed", False)
        best_i, best_s = indices[0], -1
        for i in indices:
            opt  = options[i]
            cid  = getattr(opt, "cardId", None) or getattr(opt, "index", None)
            cf   = self.card_features.get(str(cid)) if cid else None
            score = 10
            if cf:
                if cf.get("subtype") == "Supporter" and sup_played:
                    score = -1
                elif cf.get("is_draw_supporter"):
                    score = 100
                elif cf.get("is_search_card"):
                    score = 80
                elif cf.get("is_energy_accel"):
                    score = 70
                elif cf.get("is_disruption"):
                    score = 50
            if score > best_s:
                best_s, best_i = score, i
        return best_i

    # ── Pokemon selection ─────────────────────────────────────────────────────

    def _select_pokemon(self, options, minCount, obs_dict):
        scored = []
        for i, opt in enumerate(options):
            cid   = getattr(opt, "cardId", None)
            area  = getattr(opt, "area", None)
            cf    = self.card_features.get(str(cid)) if cid else None
            hp    = (cf.get("hp") or 100) if cf else 100
            score = -hp if area == 6 else hp
            scored.append((score, i))
        scored.sort(reverse=True)
        count = max(minCount, 1) if minCount > 0 else 1
        count = min(count, len(options))
        return [idx for _, idx in scored[:count]]

    def _pick_type(self, options, t):
        for i, o in enumerate(options):
            if o.type == t:
                return [i]
        return [0]

    def _random_of_type(self, options, t, minCount):
        idx = [i for i, o in enumerate(options) if o.type == t]
        if not idx:
            idx = list(range(len(options)))
        return random.sample(idx, min(max(minCount,1), len(idx)))


# ── Factory ───────────────────────────────────────────────────────────────────

def make_agent(deck, card_features=None, attacks_db=None):
    bot = RuleAgent(deck, card_features, attacks_db)
    def agent(obs_dict):
        return bot.act(obs_dict)
    return agent


if __name__ == "__main__":
    import random as rnd
    from cg.sim import lib
    from environment.simulator_wrapper import load_deck_csv, run_game, SimulatorWrapper

    deck = load_deck_csv(ROOT / "deck.csv")
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

    # measure baseline
    def measure(name, a0, a1, games=20):
        p0w = p1w = tt = ta = 0
        for i in range(games):
            sim = SimulatorWrapper(deck, deck)
            obs_dict = sim.reset()
            atk_c = 0
            while not sim.done:
                obs = to_observation_class(obs_dict)
                if obs.select is None or len(obs.select.option)==0: break
                player = sim.current_player()
                fn = a0 if player==0 else a1
                try: action = fn(obs_dict)
                except: action = sim.safe_action()
                if action and obs.select:
                    if obs.select.option[action[0]].type==13: atk_c+=1
                obs_dict = sim.step(action)
            sim.close()
            if sim.result==0: p0w+=1
            elif sim.result==1: p1w+=1
            tt += sim.turns
            ta += atk_c
        print(f"\n{name}")
        print(f"  P0:{p0w} P1:{p1w} AvgTurns:{tt/games:.0f} AvgAtks:{ta/games:.1f}")

    print("="*50)
    measure("Random vs Random",     random_agent, random_agent)
    measure("Final(P0) vs Random",  agent_fn,     random_agent)
    measure("Random vs Final(P1)",  random_agent, agent_fn)
    measure("Final vs Final",       agent_fn,     agent_fn)
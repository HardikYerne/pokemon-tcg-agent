import sys
import json
import random
import math
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


class MCTSAgent:
    """
    Heuristic scoring agent — scores each action without simulator rollouts.
    
    Why not real MCTS:
    - Simulator has single shared state — cannot fork for parallel rollouts
    - Rollouts would corrupt the live game state
    
    Instead: score each option using board state analysis + damage lookup.
    This gives MCTS-like action selection without the simulator dependency.
    """

    def __init__(self, deck, card_features=None, attacks_db=None, verbose=False):
        self.deck          = deck
        self.card_features = card_features or {}
        self.attacks_db    = attacks_db or {}
        self.verbose       = verbose
        self._going_second = False
        self._game_start   = True

    def act(self, obs_dict: dict) -> list:
        obs = to_observation_class(obs_dict)

        if obs.select is None:
            return self.deck

        options  = obs.select.option
        n        = len(options)
        minCount = obs.select.minCount

        if n == 0:
            return []

        types = [o.type for o in options]

        # fast paths
        if T_COIN_HEAD in types:
            return self._pick_type(options, T_COIN_HEAD)
        if T_MULLIGAN in types:
            return self._random_of_type(options, T_MULLIGAN, minCount)
        if all(t == T_SELECT_POKEMON for t in types):
            return self._select_pokemon(options, minCount, obs_dict)

        # score every option
        return self._score_and_pick(options, minCount, obs_dict)

    def _score_and_pick(self, options, minCount, obs_dict) -> list:
        """Score each option and return the best one."""
        current      = obs_dict.get("current", {})
        players      = current.get("players", [{}, {}])
        my_idx       = current.get("yourIndex", 0)
        me           = players[my_idx]      if len(players) > my_idx      else {}
        opp          = players[1 - my_idx]  if len(players) > 1 - my_idx  else {}

        # board state
        opp_active   = opp.get("active", [])
        my_active    = me.get("active",  [])
        opp_hp       = opp_active[0]["hp"]  if opp_active else 9999
        my_hp        = my_active[0]["hp"]   if my_active  else 0
        my_max_hp    = my_active[0].get("maxHp", 1) if my_active else 1
        my_energy    = len(my_active[0].get("energies", [])) if my_active else 0
        my_prizes    = sum(1 for p in me.get("prize",  []) if p is None)
        opp_prizes   = sum(1 for p in opp.get("prize", []) if p is None)
        my_bench     = len(me.get("bench", []))
        first_player = current.get("firstPlayer", 0)
        turn         = current.get("turn", 0)

        if self._game_start:
            self._going_second = (my_idx != first_player)
            self._game_start   = False

        hp_pct    = my_hp / my_max_hp if my_max_hp else 1.0
        behind    = my_prizes < opp_prizes
        prizes_left = 6 - opp_prizes  # how many prizes opp still needs

        scored = []
        for i, opt in enumerate(options):
            score = self._score_option(
                opt, i, opp_hp, my_energy, my_bench,
                hp_pct, behind, self._going_second,
                my_prizes, opp_prizes, prizes_left, turn, current
            )
            scored.append((score, i))
            if self.verbose:
                tname = {0:'MUL',3:'SEL',6:'HAND',7:'PLAY',8:'BENCH',
                         9:'EVO',12:'ABIL',13:'ATK',14:'END'}.get(opt.type,'?')
                print(f"  option {i} type={tname} score={score:.1f}")

        scored.sort(reverse=True)

        if minCount == 0:
            # optional — only take if best score is positive
            if scored[0][0] > 0:
                return [scored[0][1]]
            return []

        return [scored[0][1]]

    def _score_option(self, opt, idx, opp_hp, my_energy, my_bench,
                      hp_pct, behind, going_second, my_prizes,
                      opp_prizes, prizes_left, turn, current) -> float:
        t = opt.type

        # ── ATTACK ───────────────────────────────────────────────────────────
        if t == T_ATTACK:
            dmg   = self._dmg(opt.attackId)
            score = float(dmg)

            # KO bonus — huge reward
            if dmg >= opp_hp:
                score += 10000.0

            # going second — attack is always top priority
            if going_second:
                score += 500.0

            # behind on prizes — must attack
            if behind:
                score += 300.0

            # chip damage is still good
            score += dmg * 0.5

            return score

        # ── EVOLVE ───────────────────────────────────────────────────────────
        if t == T_EVOLVE:
            return 800.0  # always evolve when possible

        # ── PLACE FROM HAND (type 6) ─────────────────────────────────────────
        if t == T_PLACE_HAND:
            if my_bench < 2:
                return 600.0   # urgent — no backup
            elif my_bench < 4:
                return 200.0   # good — build board
            return 50.0        # low priority if bench full

        # ── PLACE ON BENCH (type 8) ──────────────────────────────────────────
        if t == T_PLACE_BENCH:
            if my_bench < 2:
                return 550.0
            elif my_bench < 4:
                return 180.0
            return 40.0

        # ── PLAY CARD ────────────────────────────────────────────────────────
        if t == T_PLAY_CARD:
            sup_played = current.get("supporterPlayed", False)
            card_id    = getattr(opt, "cardId", None) or getattr(opt, "index", None)
            cf         = self.card_features.get(str(card_id)) if card_id else None

            if cf:
                if cf.get("subtype") == "Supporter" and sup_played:
                    return -100.0   # can't play 2nd supporter
                if cf.get("is_draw_supporter"):
                    return 400.0    # draw cards = high value
                if cf.get("is_search_card"):
                    return 350.0
                if cf.get("is_energy_accel"):
                    return 300.0
                if cf.get("is_disruption"):
                    return 150.0
            return 100.0

        # ── USE ABILITY ──────────────────────────────────────────────────────
        if t == T_USE_ABILITY:
            return 250.0

        # ── END TURN ─────────────────────────────────────────────────────────
        if t == T_END_TURN:
            # penalize ending turn when we could attack
            return -50.0

        # unknown type
        return 0.0

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

    def _select_pokemon(self, options, minCount, obs_dict) -> list:
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
        return [idx for _, idx in scored[:min(count, len(options))]]

    def _pick_type(self, options, t):
        for i, o in enumerate(options):
            if o.type == t: return [i]
        return [0]

    def _random_of_type(self, options, t, minCount):
        idx = [i for i,o in enumerate(options) if o.type == t]
        if not idx: idx = list(range(len(options)))
        return random.sample(idx, min(max(minCount, 1), len(idx)))


# ── Factory ───────────────────────────────────────────────────────────────────

def make_agent(deck, card_features=None, attacks_db=None):
    bot = MCTSAgent(deck, card_features, attacks_db)
    def agent(obs_dict):
        return bot.act(obs_dict)
    return agent


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random as rnd
    from cg.sim import lib
    from environment.simulator_wrapper import load_deck_csv, SimulatorWrapper
    from agent.rule_agent import make_agent as make_rule

    deck = load_deck_csv(ROOT / "deck.csv")
    with open(ROOT / "knowledge" / "card_knowledge_base.json", encoding="utf-8") as f:
        features = json.load(f)
    atk_db = {a["attackId"]: a for a in json.loads(lib.AllAttack().decode())}

    mcts  = make_agent(deck, features, atk_db)
    rule  = make_rule(deck, features, atk_db)

    def random_agent(obs_dict):
        obs = to_observation_class(obs_dict)
        if obs.select is None: return deck
        n = len(obs.select.option)
        mc = obs.select.minCount
        if n == 0: return []
        if mc == 0: return []
        return rnd.sample(list(range(n)), min(mc, n))

    def measure(name, a0, a1, games=20):
        p0w = p1w = tt = 0
        for i in range(games):
            sim = SimulatorWrapper(deck, deck)
            obs_dict = sim.reset()
            while not sim.done:
                obs = to_observation_class(obs_dict)
                if obs.select is None or len(obs.select.option) == 0: break
                player = sim.current_player()
                fn = a0 if player == 0 else a1
                try: action = fn(obs_dict)
                except: action = sim.safe_action()
                obs_dict = sim.step(action)
            sim.close()
            if sim.result == 0: p0w += 1
            elif sim.result == 1: p1w += 1
            tt += sim.turns
        print(f"{name:35} P0={p0w:2} P1={p1w:2} AvgT={tt/games:.0f}")

    print("="*60)
    print("MCTS(heuristic) vs Rule Agent")
    print("="*60)
    measure("Random vs Random",          random_agent, random_agent)
    measure("MCTS(P0) vs Random(P1)",    mcts,         random_agent)
    measure("Random(P0) vs MCTS(P1)",    random_agent, mcts)
    measure("MCTS(P0) vs Rule(P1)",      mcts,         rule)
    measure("Rule(P0) vs MCTS(P1)",      rule,         mcts)
    measure("MCTS vs MCTS",              mcts,         mcts)
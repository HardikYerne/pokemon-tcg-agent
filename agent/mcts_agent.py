import sys
import json
import random
import math
from pathlib import Path
import os
from copy import deepcopy

KAGGLE_PATH = Path("/kaggle_simulations/agent")
LOCAL_PATH  = Path(os.getcwd())
ROOT        = KAGGLE_PATH if KAGGLE_PATH.exists() else LOCAL_PATH
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sample_submission"))
sys.path.insert(0, "/kaggle_simulations/agent")

from cg.api import to_observation_class
from cg.game import battle_select


# ── Option types ──────────────────────────────────────────────────────────────
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
T_MULLIGAN       = 0


# ── Board state scorer ────────────────────────────────────────────────────────

def score_board(obs_dict: dict, my_idx: int) -> float:
    """
    Score the current board state from my_idx perspective.
    Higher = better for me.
    """
    current = obs_dict.get("current", {})
    if not current:
        return 0.0

    players = current.get("players", [{}, {}])
    me  = players[my_idx]      if len(players) > my_idx      else {}
    opp = players[1 - my_idx]  if len(players) > 1 - my_idx  else {}

    def prizes_taken(p):
        return sum(1 for x in p.get("prize", []) if x is None)

    def active_hp_pct(p):
        a = p.get("active", [])
        if not a: return 0.0
        return a[0]["hp"] / a[0].get("maxHp", 1)

    def energy_count(p):
        a = p.get("active", [])
        return len(a[0].get("energies", [])) if a else 0

    my_prizes   = prizes_taken(me)
    opp_prizes  = prizes_taken(opp)
    my_hp_pct   = active_hp_pct(me)
    opp_hp_pct  = active_hp_pct(opp)
    my_energy   = energy_count(me)
    my_bench    = len(me.get("bench", []))

    # check terminal
    result = current.get("result", -1)
    if result == 0:
        return 1000.0   # win
    elif result > 0:
        return -1000.0  # loss

    score = 0.0

    # prize race — most important
    score += (my_prizes - opp_prizes) * 50.0

    # HP advantage
    score += (my_hp_pct - opp_hp_pct) * 20.0

    # energy advantage
    score += my_energy * 5.0

    # bench presence
    score += my_bench * 3.0

    # deck size (don't deck out)
    my_deck  = me.get("deckCount", 30)
    opp_deck = opp.get("deckCount", 30)
    score += (my_deck - opp_deck) * 0.5

    return score


# ── MCTS Node ─────────────────────────────────────────────────────────────────

class MCTSNode:
    def __init__(self, action=None, parent=None):
        self.action   = action    # action that led to this node
        self.parent   = parent
        self.children = []
        self.visits   = 0
        self.value    = 0.0
        self.untried  = None      # untried actions

    def ucb1(self, c=1.41) -> float:
        if self.visits == 0:
            return float('inf')
        exploit = self.value / self.visits
        explore = c * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploit + explore

    def best_child(self):
        return max(self.children, key=lambda n: n.ucb1())

    def best_action(self):
        """Return action of most visited child."""
        if not self.children:
            return None
        return max(self.children, key=lambda n: n.visits).action


# ── MCTS Agent ────────────────────────────────────────────────────────────────

class MCTSAgent:
    """
    Monte Carlo Tree Search agent for Pokémon TCG.

    How it works:
    1. From current state, simulate N random games (rollouts)
    2. Each rollout plays randomly until game ends or depth limit
    3. Actions that lead to wins get higher scores
    4. Pick action with highest win rate

    Simulations: 50 per turn (fast enough for 10-min limit)
    Rollout depth: 10 turns ahead
    """

    def __init__(self, deck, card_features=None, attacks_db=None,
                 simulations=50, rollout_depth=10, verbose=False):
        self.deck          = deck
        self.card_features = card_features or {}
        self.attacks_db    = attacks_db or {}
        self.simulations   = simulations
        self.rollout_depth = rollout_depth
        self.verbose       = verbose

        # import rule agent for rollout policy
        from agent.rule_agent import RuleAgent
        self._rule_agent = RuleAgent(deck, card_features, attacks_db)

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

        # non-turn decisions — use rule agent directly (faster)
        if T_COIN_HEAD in types:
            return self._pick_type(options, T_COIN_HEAD)
        if T_MULLIGAN in types:
            return self._random_of_type(options, T_MULLIGAN, minCount)
        if all(t == T_SELECT_POKEMON for t in types):
            return self._select_pokemon(options, minCount, obs_dict)

        # if only 1 option — no need for MCTS
        if n == 1:
            return [0] if minCount > 0 else []

        # if end turn is only non-trivial option — just end
        non_end = [o for o in options if o.type != T_END_TURN]
        if not non_end:
            return [next(i for i,o in enumerate(options) if o.type == T_END_TURN)]

        # run MCTS
        current = obs_dict.get("current", {})
        my_idx  = current.get("yourIndex", 0) if current else 0

        best_action = self._mcts(obs_dict, options, minCount, my_idx)
        return best_action

    def _mcts(self, obs_dict, options, minCount, my_idx) -> list:
        """Run MCTS simulations and return best action."""
        n = len(options)

        # build candidate actions
        candidates = []
        for i in range(n):
            opt = options[i]
            # always include attacks and evolves
            if opt.type in (T_ATTACK, T_EVOLVE):
                candidates.append([i])
            elif opt.type == T_END_TURN:
                candidates.append([i])
            elif opt.type in (T_PLACE_HAND, T_PLACE_BENCH):
                candidates.append([i])
            elif opt.type == T_PLAY_CARD:
                candidates.append([i])

        if not candidates:
            if minCount == 0: return []
            return [random.randint(0, n-1)]

        # score each candidate with rollouts
        scores = {str(c): 0.0 for c in candidates}
        visits = {str(c): 0   for c in candidates}

        for sim_i in range(self.simulations):
            # pick candidate (UCB1 style)
            action = self._ucb_select(candidates, scores, visits, sim_i)

            # simulate from this action
            result = self._rollout(obs_dict, action, my_idx)

            # update scores
            key = str(action)
            scores[key] += result
            visits[key] += 1

        # pick best action
        best = max(candidates,
                   key=lambda c: scores[str(c)] / max(visits[str(c)], 1))

        if self.verbose:
            print(f"  [mcts] sims={self.simulations} candidates={len(candidates)}")
            for c in candidates:
                k = str(c)
                v = visits[k]
                s = scores[k] / v if v > 0 else 0
                opt = options[c[0]]
                print(f"    action={c} type={opt.type} visits={v} score={s:.2f}")

        return best

    def _ucb_select(self, candidates, scores, visits, total) -> list:
        """Select candidate using UCB1."""
        best_c = None
        best_s = float('-inf')

        for c in candidates:
            k = str(c)
            v = visits[k]
            if v == 0:
                return c  # always try unvisited first
            exploit = scores[k] / v
            explore = 1.41 * math.sqrt(math.log(total + 1) / v)
            ucb = exploit + explore
            if ucb > best_s:
                best_s, best_c = ucb, c

        return best_c

    def _rollout(self, obs_dict, first_action, my_idx) -> float:
        """
        Simulate game from current state.
        First action is forced, rest use rule agent policy.
        Returns score: positive = good for my_idx, negative = bad.
        """
        try:
            # execute first action
            next_obs = battle_select(first_action)

            # rollout with rule agent for depth turns
            for depth in range(self.rollout_depth):
                obs = to_observation_class(next_obs)

                # check terminal
                result = next_obs.get("current", {}).get("result", -1)
                if result >= 0:
                    score = score_board(next_obs, my_idx)
                    return score

                if obs.select is None or len(obs.select.option) == 0:
                    break

                # use rule agent for rollout policy
                try:
                    action = self._rule_agent.act(next_obs)
                except:
                    action = self._safe_action(obs)

                if not action:
                    break

                next_obs = battle_select(action)

            # evaluate final state
            return score_board(next_obs, my_idx)

        except Exception as e:
            return 0.0

    def _safe_action(self, obs) -> list:
        options  = obs.select.option
        n        = len(options)
        minCount = obs.select.minCount
        if n == 0: return []
        if minCount == 0: return []
        return [random.randint(0, n-1)]

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
        return random.sample(idx, min(max(minCount,1), len(idx)))


# ── Factory ───────────────────────────────────────────────────────────────────

def make_agent(deck, card_features=None, attacks_db=None,
               simulations=50, rollout_depth=10):
    bot = MCTSAgent(deck, card_features, attacks_db,
                    simulations, rollout_depth)
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

    mcts_agent = make_agent(deck, features, atk_db, simulations=30, rollout_depth=8)
    rule_agent = make_rule(deck, features, atk_db)

    def measure(name, a0, a1, games=10):
        p0w = p1w = tt = 0
        for i in range(games):
            sim = SimulatorWrapper(deck, deck)
            obs_dict = sim.reset()
            while not sim.done:
                obs = to_observation_class(obs_dict)
                if obs.select is None or len(obs.select.option)==0: break
                player = sim.current_player()
                fn = a0 if player==0 else a1
                try: action = fn(obs_dict)
                except: action = sim.safe_action()
                obs_dict = sim.step(action)
            sim.close()
            if sim.result==0: p0w+=1
            elif sim.result==1: p1w+=1
            tt += sim.turns
        print(f"{name}: P0={p0w} P1={p1w} AvgT={tt/games:.0f}")

    print("MCTS vs Rule Agent (10 games each):")
    measure("MCTS(P0) vs Rule(P1)", mcts_agent, rule_agent)
    measure("Rule(P0) vs MCTS(P1)", rule_agent, mcts_agent)
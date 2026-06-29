import sys
import json
from pathlib import Path
import os

KAGGLE_PATH = Path("/kaggle_simulations/agent")
LOCAL_PATH  = Path(os.getcwd())
ROOT        = KAGGLE_PATH if KAGGLE_PATH.exists() else LOCAL_PATH
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sample_submission"))
sys.path.insert(0, "/kaggle_simulations/agent")

from cg.api import to_observation_class

# ── Type system ───────────────────────────────────────────────────────────────
TYPE_NAME = {
    0: "Colorless", 1: "Grass", 2: "Fire", 3: "Water",
    4: "Lightning", 5: "Psychic", 6: "Fighting",
    7: "Dark", 8: "Metal", 9: "Dragon", 10: "Fairy"
}

# weakness map: pokemon_type -> weak_against_type
# e.g. Grass(1) is weak to Fire(2)
WEAKNESS_MAP = {
    1: 2,   # Grass -> Fire
    2: 3,   # Fire -> Water
    3: 4,   # Water -> Lightning
    4: 6,   # Lightning -> Fighting
    5: 7,   # Psychic -> Dark
    6: 1,   # Fighting -> Grass (Psychic in main TCG but Grass here)
    7: 6,   # Dark -> Fighting
    8: 2,   # Metal -> Fire
    9: 4,   # Dragon -> Dragon (Lightning here)
    0: None # Colorless -> no weakness
}

# energy type -> pokemon type mapping
ENERGY_TO_TYPE = {
    1: 1,   # Grass energy -> Grass type
    2: 2,   # Fire energy -> Fire type
    3: 3,   # Water energy -> Water type
    4: 4,   # Lightning energy -> Lightning type
    5: 5,   # Psychic energy -> Psychic type
    6: 6,   # Fighting energy -> Fighting type
    7: 7,   # Dark energy -> Dark type
    8: 8,   # Metal energy -> Metal type
    0: 0,   # Colorless -> any
}


class RAGKnowledge:
    """
    Retrieval Augmented Generation for Pokémon TCG decisions.
    
    Pre-computes card knowledge and retrieves relevant info
    based on current game state to improve attack selection.
    """

    def __init__(self, attacks_db: dict, card_features: dict):
        self.attacks_db    = attacks_db
        self.card_features = card_features

        # build card lookup from simulator
        self._build_card_index()

    def _build_card_index(self):
        """Build fast lookup indexes."""
        # card_id -> weakness type
        self.weakness_index = {}
        # card_id -> pokemon_type
        self.type_index = {}
        # card_id -> hp
        self.hp_index = {}
        # attack_id -> damage
        self.damage_index = {}
        # attack_id -> energy cost list
        self.cost_index = {}

        # from attacks_db
        for aid, atk in self.attacks_db.items():
            self.damage_index[aid] = atk.get("damage", 0)
            self.cost_index[aid]   = atk.get("energies", [])

        print(f"[RAG] Indexed {len(self.damage_index)} attacks")

    def retrieve_attack_context(self, obs_dict: dict) -> dict:
        """
        Retrieve relevant knowledge for current game state.
        Returns context dict with strategic recommendations.
        """
        current = obs_dict.get("current", {})
        players = current.get("players", [{}, {}])
        my_idx  = current.get("yourIndex", 0)
        me      = players[my_idx]     if len(players) > my_idx     else {}
        opp     = players[1-my_idx]   if len(players) > 1-my_idx   else {}

        opp_active = opp.get("active", [])
        my_active  = me.get("active",  [])

        context = {
            "opp_weakness":      None,   # opponent weakness type
            "opp_hp":            9999,
            "opp_type":          None,
            "my_energy_types":   [],     # energy types attached to active
            "weakness_bonus":    False,  # can we hit weakness?
            "ko_possible":       False,
            "recommended_atk":   None,   # best attack id
        }

        if not opp_active or not my_active:
            return context

        opp_poke = opp_active[0]
        my_poke  = my_active[0]

        # retrieve opponent info
        opp_card_id = opp_poke.get("id")
        opp_hp      = opp_poke.get("hp", 9999)
        context["opp_hp"] = opp_hp

        # get weakness from card features
        cf = self.card_features.get(str(opp_card_id)) if opp_card_id else None
        if cf:
            weakness_str = cf.get("weakness", "")
            if weakness_str:
                # parse weakness type from string like "{F}" or "{W}"
                w_map = {"{G}":1,"{R}":2,"{W}":3,"{L}":4,
                         "{P}":5,"{F}":6,"{D}":7,"{M}":8}
                for sym, wtype in w_map.items():
                    if sym in str(weakness_str):
                        context["opp_weakness"] = wtype
                        break

        # get my energy types
        my_energies = my_poke.get("energies", [])
        context["my_energy_types"] = my_energies

        # check if we can hit weakness
        if context["opp_weakness"] is not None:
            for energy in my_energies:
                if ENERGY_TO_TYPE.get(energy) == context["opp_weakness"]:
                    context["weakness_bonus"] = True
                    break

        return context

    def score_attack_with_rag(self, attack_id, context: dict) -> float:
        """
        Score an attack using RAG context.
        Returns bonus score to add to base damage score.
        """
        if not attack_id:
            return 0.0

        dmg      = self.damage_index.get(attack_id, 0)
        opp_hp   = context.get("opp_hp", 9999)
        weakness = context.get("opp_weakness")
        w_bonus  = context.get("weakness_bonus", False)
        cost     = self.cost_index.get(attack_id, [])

        bonus = 0.0

        # weakness multiplier — 2x damage in TCG
        if weakness is not None:
            effective_dmg = dmg * 2
            if effective_dmg >= opp_hp:
                bonus += 5000.0  # weakness KO bonus
            else:
                bonus += dmg * 0.5  # weakness chip bonus

        # energy efficiency bonus
        n_cost = len([e for e in cost if e != 0])
        if n_cost > 0 and dmg > 0:
            dpe = dmg / n_cost
            bonus += dpe * 0.3

        # colorless cost bonus — more consistent
        colorless_ratio = len([e for e in cost if e == 0]) / max(len(cost), 1)
        bonus += colorless_ratio * 20.0

        return bonus

    def get_strategic_recommendation(self, obs_dict: dict) -> str:
        """Return human-readable strategic recommendation."""
        ctx = self.retrieve_attack_context(obs_dict)
        recs = []

        if ctx["opp_weakness"]:
            wname = TYPE_NAME.get(ctx["opp_weakness"], "?")
            recs.append(f"Opponent weak to {wname}")

        if ctx["weakness_bonus"]:
            recs.append("Can hit weakness with current energy!")

        opp_hp = ctx["opp_hp"]
        if opp_hp < 100:
            recs.append(f"Opponent low HP ({opp_hp}) — KO possible")

        return " | ".join(recs) if recs else "No special conditions"


# ── RAG-Enhanced Agent ────────────────────────────────────────────────────────

class RAGAgent:
    """
    Agent enhanced with RAG knowledge retrieval.
    Uses heuristic scoring + RAG context for better attack selection.
    """

    def __init__(self, deck, card_features=None, attacks_db=None, verbose=False):
        self.deck          = deck
        self.card_features = card_features or {}
        self.attacks_db    = attacks_db or {}
        self.verbose       = verbose
        self._going_second = False
        self._game_start   = True

        # init RAG
        self.rag = RAGKnowledge(self.attacks_db, self.card_features)

    # ── Option types ──────────────────────────────────────────────────────────
    T_MULLIGAN = 0; T_COIN_HEAD = 1; T_SELECT_POKEMON = 3
    T_PLACE_HAND = 6; T_PLAY_CARD = 7; T_PLACE_BENCH = 8
    T_EVOLVE = 9; T_USE_ABILITY = 12; T_ATTACK = 13; T_END_TURN = 14

    def act(self, obs_dict: dict) -> list:
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return self.deck

        options  = obs.select.option
        n        = len(options)
        minCount = obs.select.minCount

        if n == 0: return []

        types = [o.type for o in options]

        if self.T_COIN_HEAD in types:
            return self._pick_type(options, self.T_COIN_HEAD)
        if self.T_MULLIGAN in types:
            return self._random_of_type(options, self.T_MULLIGAN, minCount)
        if all(t == self.T_SELECT_POKEMON for t in types):
            return self._select_pokemon(options, minCount, obs_dict)

        return self._score_and_pick(options, minCount, obs_dict)

    def _score_and_pick(self, options, minCount, obs_dict) -> list:
        current    = obs_dict.get("current", {})
        players    = current.get("players", [{}, {}])
        my_idx     = current.get("yourIndex", 0)
        me         = players[my_idx]    if len(players) > my_idx    else {}
        opp        = players[1-my_idx]  if len(players) > 1-my_idx  else {}

        opp_active = opp.get("active", [])
        my_active  = me.get("active",  [])
        opp_hp     = opp_active[0]["hp"] if opp_active else 9999
        my_hp      = my_active[0]["hp"]  if my_active  else 0
        my_max_hp  = my_active[0].get("maxHp", 1) if my_active else 1
        my_bench   = len(me.get("bench", []))
        my_prizes  = sum(1 for p in me.get("prize",[]) if p is None)
        opp_prizes = sum(1 for p in opp.get("prize",[]) if p is None)
        first_p    = current.get("firstPlayer", 0)

        if self._game_start:
            self._going_second = (my_idx != first_p)
            self._game_start   = False

        behind  = my_prizes < opp_prizes
        hp_pct  = my_hp / my_max_hp if my_max_hp else 1.0

        # retrieve RAG context
        rag_ctx = self.rag.retrieve_attack_context(obs_dict)

        if self.verbose:
            rec = self.rag.get_strategic_recommendation(obs_dict)
            print(f"  [RAG] {rec}")

        scored = []
        for i, opt in enumerate(options):
            score = self._score_option(opt, opp_hp, my_bench,
                                       behind, self._going_second,
                                       my_prizes, opp_prizes,
                                       current, rag_ctx)
            scored.append((score, i))

        scored.sort(reverse=True)

        if minCount == 0:
            if scored[0][0] > 0:
                return [scored[0][1]]
            return []

        count = min(minCount, len(scored))
        return [idx for _, idx in scored[:count]]

    def _score_option(self, opt, opp_hp, my_bench,
                      behind, going_second, my_prizes,
                      opp_prizes, current, rag_ctx) -> float:
        t = opt.type

        if t == self.T_ATTACK:
            dmg   = self._dmg(opt.attackId)
            score = float(dmg)

            # KO bonus
            if dmg >= opp_hp:
                score += 10000.0

            # RAG weakness bonus
            rag_bonus = self.rag.score_attack_with_rag(opt.attackId, rag_ctx)
            score += rag_bonus

            # weakness KO check (2x damage)
            if rag_ctx.get("opp_weakness"):
                if dmg * 2 >= opp_hp:
                    score += 8000.0  # weakness KO!

            if going_second: score += 500.0
            if behind:       score += 300.0
            score += dmg * 0.5
            return score

        if t == self.T_EVOLVE:     return 800.0
        if t == self.T_PLACE_HAND:
            if my_bench < 2: return 600.0
            if my_bench < 4: return 200.0
            return 50.0
        if t == self.T_PLACE_BENCH:
            if my_bench < 2: return 550.0
            if my_bench < 4: return 180.0
            return 40.0
        if t == self.T_PLAY_CARD:
            sup_played = current.get("supporterPlayed", False)
            cid = getattr(opt, "cardId", None) or getattr(opt, "index", None)
            cf  = self.card_features.get(str(cid)) if cid else None
            if cf:
                if cf.get("subtype") == "Supporter" and sup_played: return -100.0
                if cf.get("is_draw_supporter"):  return 400.0
                if cf.get("is_search_card"):     return 350.0
                if cf.get("is_energy_accel"):    return 300.0
                if cf.get("is_disruption"):      return 150.0
            return 100.0
        if t == self.T_USE_ABILITY: return 250.0
        if t == self.T_END_TURN:    return -50.0
        return 0.0

    def _dmg(self, attack_id) -> int:
        if not attack_id: return 0
        atk = self.attacks_db.get(attack_id)
        if atk: return atk.get("damage", 0)
        cf = self.card_features.get(str(attack_id))
        if cf: return cf.get("attack_damage") or 0
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
        import random
        idx = [i for i,o in enumerate(options) if o.type == t]
        if not idx: idx = list(range(len(options)))
        return random.sample(idx, min(max(minCount, 1), len(idx)))


def make_agent(deck, card_features=None, attacks_db=None):
    bot = RAGAgent(deck, card_features, attacks_db)
    def agent(obs_dict):
        return bot.act(obs_dict)
    return agent


if __name__ == "__main__":
    import random as rnd
    from cg.sim import lib
    from environment.simulator_wrapper import load_deck_csv, SimulatorWrapper
    from agent.rule_agent import make_agent as make_rule

    deck = load_deck_csv(ROOT / "deck.csv")
    with open(ROOT / "knowledge" / "card_knowledge_base.json", encoding="utf-8") as f:
        features = json.load(f)
    atk_db = {a["attackId"]: a for a in json.loads(lib.AllAttack().decode())}

    rag  = make_agent(deck, features, atk_db)
    rule = make_rule(deck, features, atk_db)

    def rand(obs_dict):
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
                if obs.select is None or len(obs.select.option)==0: break
                n  = len(obs.select.option)
                mc = obs.select.minCount
                player = sim.current_player()
                fn = a0 if player==0 else a1
                action = fn(obs_dict)
                if not action and mc > 0: action = [0]
                if action and max(action) >= n: action = [0]
                obs_dict = sim.step(action)
            sim.close()
            if sim.result==0: p0w+=1
            elif sim.result==1: p1w+=1
            tt += sim.turns
        print(f"{name:35} P0={p0w} P1={p1w} AvgT={tt/games:.0f}")

    print("="*55)
    print("RAG Agent vs Rule Agent")
    print("="*55)
    measure("Random vs Random",         rand, rand)
    measure("RAG(P0) vs Random(P1)",    rag,  rand)
    measure("Random(P0) vs RAG(P1)",    rand, rag)
    measure("RAG(P0) vs Rule(P1)",      rag,  rule)
    measure("Rule(P0) vs RAG(P1)",      rule, rag)
    measure("RAG vs RAG",               rag,  rag)
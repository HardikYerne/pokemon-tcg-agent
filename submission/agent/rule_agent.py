import sys
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sample_submission"))

from cg.api import to_observation_class
from environment.simulator_wrapper import OPTION_TYPE


# ── Option type constants ─────────────────────────────────────────────────────
T_MULLIGAN      = 0
T_COIN_HEAD     = 1
T_COIN_TAIL     = 2
T_SELECT_POKEMON = 3
T_PLAY_CARD     = 7
T_PLACE_BENCH   = 8
T_EVOLVE        = 9
T_USE_ABILITY   = 12
T_ATTACK        = 13
T_END_TURN      = 14


class RuleAgent:
    """
    Rule-based Pokémon TCG agent.

    Decision priority each turn:
      1. Attack if can KO opponent active
      2. Evolve active/bench Pokémon
      3. Place Pokémon on bench (build board)
      4. Play trainer cards from hand
      5. Use ability
      6. Attack with best available attack
      7. End turn
    
    For non-turn decisions (coin flips, select Pokémon, mulligan):
      Uses strategic defaults.
    """

    def __init__(self, deck: list, card_features: dict = None, verbose: bool = False):
        self.deck          = deck          # 60 card IDs
        self.card_features = card_features or {}  # from card_knowledge_base.json
        self.verbose       = verbose
        self.turn_count    = 0

    # ── Main entry point ──────────────────────────────────────────────────────

    def act(self, obs_dict: dict) -> list:
        """
        Main agent function — matches the Kaggle submission signature.
        obs_dict: raw observation dict from simulator
        Returns: list[int] — indices into obs.select.option
        """
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

        # get option types present
        types = [o.type for o in options]

        if self.verbose:
            type_names = [OPTION_TYPE.get(t, str(t)) for t in types]
            print(f"  [agent] turn={self.turn_count} "
                  f"n={n} min={minCount} types={type_names}")

        # ── route by decision type ────────────────────────────────────────────

        # coin flip — always pick heads (index 0 = HEAD)
        if T_COIN_HEAD in types:
            return self._pick(options, T_COIN_HEAD, minCount)

        # mulligan — pick any basic (random among options)
        if T_MULLIGAN in types:
            return self._random_of_type(options, T_MULLIGAN, minCount)

        # select pokemon (active/bench/prize) — pick strategically
        if all(t == T_SELECT_POKEMON for t in types):
            return self._select_pokemon(options, minCount, maxCount, obs_dict)

        # main turn decisions
        action = self._main_turn_action(options, minCount, maxCount, obs_dict)
        self.turn_count += 1
        return action

    # ── Main turn logic ───────────────────────────────────────────────────────

    def _main_turn_action(self, options, minCount, maxCount, obs_dict) -> list:
        """Priority-ordered main turn decision."""
        types = [o.type for o in options]

        # 1. ATTACK — highest priority
        if T_ATTACK in types:
            attack_indices = [i for i, o in enumerate(options)
                              if o.type == T_ATTACK]

            # try to find best attack
            best = self._best_attack(attack_indices, options, obs_dict)
            if best is not None:
                if self.verbose:
                    print(f"  [agent] → ATTACK index={best}")
                return [best]

        # 2. EVOLVE — evolve Pokémon when possible
        if T_EVOLVE in types:
            evolve_idx = [i for i, o in enumerate(options)
                          if o.type == T_EVOLVE]
            if evolve_idx:
                if self.verbose:
                    print(f"  [agent] → EVOLVE")
                return [evolve_idx[0]]

        # 3. PLACE ON BENCH — build board presence
        if T_PLACE_BENCH in types:
            bench_indices = [i for i, o in enumerate(options)
                             if o.type == T_PLACE_BENCH]
            if bench_indices:
                chosen = self._best_bench_placement(bench_indices, options, obs_dict)
                if self.verbose:
                    print(f"  [agent] → BENCH index={chosen}")
                return [chosen]

        # 4. PLAY CARD from hand
        if T_PLAY_CARD in types:
            card_indices = [i for i, o in enumerate(options)
                            if o.type == T_PLAY_CARD]
            if card_indices:
                chosen = self._best_card_to_play(card_indices, options, obs_dict)
                if self.verbose:
                    print(f"  [agent] → PLAY_CARD index={chosen}")
                return [chosen]

        # 5. USE ABILITY
        if T_USE_ABILITY in types:
            ability_idx = [i for i, o in enumerate(options)
                           if o.type == T_USE_ABILITY]
            if ability_idx:
                if self.verbose:
                    print(f"  [agent] → USE_ABILITY")
                return [ability_idx[0]]

        # 6. END TURN — pass
        if T_END_TURN in types:
            end_idx = next(i for i, o in enumerate(options)
                           if o.type == T_END_TURN)
            if self.verbose:
                print(f"  [agent] → END_TURN")
            return [end_idx]

        # 7. fallback — random safe choice
        if minCount == 0:
            return []
        count = min(minCount, len(options))
        return random.sample(list(range(len(options))), count)

    # ── Attack selection ──────────────────────────────────────────────────────

    def _best_attack(self, attack_indices, options, obs_dict) -> int:
        """
        Choose best attack index.
        Priority: attack that KOs opponent > highest damage > first available
        """
        current    = obs_dict.get("current", {})
        players    = current.get("players", [{}, {}])
        my_idx     = current.get("yourIndex", 0)
        opp        = players[1 - my_idx] if len(players) > 1 else {}
        opp_active = opp.get("active", [])
        opp_hp     = opp_active[0]["hp"] if opp_active else 9999

        best_idx   = None
        best_score = -1

        for i in attack_indices:
            opt       = options[i]
            attack_id = opt.attackId
            dmg       = self._get_attack_damage(attack_id)

            # score: KO = 10000 bonus, else just damage
            score = dmg
            if dmg >= opp_hp:
                score += 10000  # KO bonus

            if score > best_score:
                best_score = score
                best_idx   = i

        return best_idx

    def _get_attack_damage(self, attack_id) -> int:
        """Look up attack damage from card features."""
        if not attack_id:
            return 0
        # attack_id maps to a card in our knowledge base
        # search by card_id since attack_id is the card's attack
        cf = self.card_features.get(str(attack_id))
        if cf:
            return cf.get("attack_damage") or 0
        return 30  # default estimate

    # ── Bench placement ───────────────────────────────────────────────────────

    def _best_bench_placement(self, bench_indices, options, obs_dict) -> int:
        """
        Choose which Pokémon to place on bench.
        Prefer: higher HP basics, evolution targets
        """
        best_idx   = bench_indices[0]
        best_score = -1

        for i in bench_indices:
            opt    = options[i]
            card_id = getattr(opt, "cardId", None) or getattr(opt, "index", None)
            cf     = self.card_features.get(str(card_id)) if card_id else None

            score = 0
            if cf:
                hp    = cf.get("hp") or 0
                score = hp  # prefer higher HP
                # bonus for cards that evolve into something
                if cf.get("subtype") == "Basic":
                    score += 10

            if score > best_score:
                best_score = score
                best_idx   = i

        return best_idx

    # ── Card play selection ───────────────────────────────────────────────────

    def _best_card_to_play(self, card_indices, options, obs_dict) -> int:
        """
        Choose best trainer card to play.
        Priority: draw supporters > search cards > other
        """
        current        = obs_dict.get("current", {})
        supporter_played = current.get("supporterPlayed", False)

        best_idx   = card_indices[0]
        best_score = -1

        for i in card_indices:
            opt     = options[i]
            card_id = getattr(opt, "cardId", None) or getattr(opt, "index", None)
            cf      = self.card_features.get(str(card_id)) if card_id else None

            score = 10  # base score for playing any card

            if cf:
                # don't replay supporter if already played
                if cf.get("subtype") == "Supporter" and supporter_played:
                    score = -1
                elif cf.get("is_draw_supporter"):
                    score = 100  # draw cards = high value
                elif cf.get("is_search_card"):
                    score = 80
                elif cf.get("is_energy_accel"):
                    score = 70
                elif cf.get("is_disruption"):
                    score = 60

            if score > best_score:
                best_score = score
                best_idx   = i

        return best_idx

    # ── Pokémon selection ─────────────────────────────────────────────────────

    def _select_pokemon(self, options, minCount, maxCount, obs_dict) -> list:
        """
        Handle SELECT_POKEMON decisions — choosing active, bench target, etc.
        Strategy: prefer highest HP Pokémon as active,
                  prefer lowest HP for prize selection (take easiest prize)
        """
        current  = obs_dict.get("current", {})
        context  = obs_dict.get("select", {}).get("context", 0)

        scored = []
        for i, opt in enumerate(options):
            card_id = getattr(opt, "cardId", None)
            area    = getattr(opt, "area", None)
            cf      = self.card_features.get(str(card_id)) if card_id else None
            hp      = cf.get("hp") or 100 if cf else 100

            # area 6 = opponent's field (taking prizes) → prefer low HP targets
            if area == 6:
                score = -hp   # lower HP = easier KO = better prize
            else:
                score = hp    # higher HP = better active/bench

            scored.append((score, i))

        scored.sort(reverse=True)
        count   = max(minCount, 1) if minCount > 0 else 1
        count   = min(count, len(options))
        chosen  = [idx for _, idx in scored[:count]]
        return chosen

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pick(self, options, target_type, minCount) -> list:
        """Pick first option of target_type."""
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


# ── Kaggle submission wrapper ─────────────────────────────────────────────────

def make_agent(deck: list, card_features: dict = None):
    """
    Factory — returns the agent() function for Kaggle submission.
    Usage in main.py:
        from agent.rule_agent import make_agent
        agent = make_agent(deck)
    """
    bot = RuleAgent(deck, card_features)

    def agent(obs_dict: dict) -> list:
        return bot.act(obs_dict)

    return agent


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from environment.simulator_wrapper import (
        SimulatorWrapper, load_deck_csv, run_game
    )

    deck_path = ROOT / "sample_submission" / "deck.csv"
    deck      = load_deck_csv(deck_path)

    # load card features
    kb_path  = ROOT / "knowledge" / "card_knowledge_base.json"
    features = {}
    if kb_path.exists():
        with open(kb_path, encoding="utf-8") as f:
            features = json.load(f)
        print(f"[rule_agent] Loaded {len(features)} card features")

    # create agents
    rule_agent = make_agent(deck, features)

    def random_agent(obs_dict):
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return deck
        n        = len(obs.select.option)
        minCount = obs.select.minCount
        if n == 0: return []
        if minCount == 0: return []
        return random.sample(list(range(n)), min(minCount, n))

    # run 10 games: rule vs random
    print("\n[rule_agent] Rule agent vs Random agent — 10 games")
    print("─" * 50)

    rule_wins   = 0
    random_wins = 0
    errors      = 0
    total_turns = 0

    for i in range(10):
        # alternate who goes first
        if i % 2 == 0:
            result = run_game(deck, deck,
                              agent0_fn=rule_agent,
                              agent1_fn=random_agent)
            if result["winner"] == 0:
                rule_wins += 1
            elif result["winner"] == 1:
                random_wins += 1
        else:
            result = run_game(deck, deck,
                              agent0_fn=random_agent,
                              agent1_fn=rule_agent)
            if result["winner"] == 1:
                rule_wins += 1
            elif result["winner"] == 0:
                random_wins += 1

        if result["error"]:
            errors += 1
        total_turns += result["turns"]
        print(f"  Game {i+1:2d}: Winner=Player {result['winner']} "
              f"Turns={result['turns']:3d} Error={result['error']}")

    avg_turns = total_turns / 10
    print(f"\n── Results ─────────────────────────────────")
    print(f"  Rule agent wins  : {rule_wins}/10")
    print(f"  Random agent wins: {random_wins}/10")
    print(f"  Errors           : {errors}")
    print(f"  Avg turns/game   : {avg_turns:.1f}")
    print(f"────────────────────────────────────────────")
import sys
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sample_submission"))

from cg.game import battle_start, battle_finish, battle_select
from cg.api  import Observation, to_observation_class


class SimulatorWrapper:

    def __init__(self, deck0: list, deck1: list):
        if len(deck0) != 60 or len(deck1) != 60:
            raise ValueError("Each deck must have exactly 60 cards")
        self.deck0     = deck0
        self.deck1     = deck1
        self.done      = False
        self.result    = None
        self.turns     = 0
        self._obs_dict = None

    def reset(self) -> dict:
        obs_dict, start_data = battle_start(self.deck0, self.deck1)
        if obs_dict is None:
            raise RuntimeError(f"Battle failed to start. errorType={start_data.errorType}")
        self.done      = False
        self.result    = None
        self.turns     = 0
        self._obs_dict = obs_dict
        return obs_dict

    def step(self, select_list: list) -> dict:
        if self.done:
            raise RuntimeError("Battle already finished. Call reset().")
        obs_dict       = battle_select(select_list)
        self._obs_dict = obs_dict
        self.turns    += 1
        if self._is_terminal(obs_dict):
            self.done   = True
            self.result = self._get_winner(obs_dict)
        return obs_dict

    def close(self):
        battle_finish()

    def get_observation(self) -> Observation:
        return to_observation_class(self._obs_dict)

    def get_legal_actions(self) -> list:
        obs = to_observation_class(self._obs_dict)
        if obs.select is None:
            return []
        return list(range(len(obs.select.option)))

    def safe_action(self) -> list:
        """Return a safe random legal action respecting minCount."""
        obs = to_observation_class(self._obs_dict)
        if obs.select is None:
            return []
        n        = len(obs.select.option)
        minCount = obs.select.minCount
        if n == 0:
            return []
        if minCount == 0:
            return []
        count = min(minCount, n)
        return random.sample(list(range(n)), count)

    def current_player(self) -> int:
        current = self._obs_dict.get("current", {})
        return current.get("yourIndex", 0) if current else 0

    def _is_terminal(self, obs_dict: dict) -> bool:
        """Game ends when result >= 0 (not -1) OR options list empty."""
        current = obs_dict.get("current", {})
        if current and current.get("result", -1) >= 0:
            return True
        obs = to_observation_class(obs_dict)
        if obs.select and len(obs.select.option) == 0:
            return True
        return False

    def _get_winner(self, obs_dict: dict) -> int:
        current = obs_dict.get("current", {})
        if current:
            result     = current.get("result", -1)
            your_index = current.get("yourIndex", 0)
            if result == 0:
                return your_index
            elif result > 0:
                return 1 - your_index
        return -1

    def get_board_state(self) -> dict:
        current = self._obs_dict.get("current", {})
        if not current:
            return {}
        players = current.get("players", [{}, {}])
        my_idx  = current.get("yourIndex", 0)
        op_idx  = 1 - my_idx
        me      = players[my_idx]  if len(players) > my_idx else {}
        opp     = players[op_idx]  if len(players) > op_idx else {}

        def prizes_taken(p):
            return sum(1 for x in p.get("prize", []) if x is None)
        def active_hp(p):
            a = p.get("active", [])
            return a[0]["hp"] if a else 0
        def active_max_hp(p):
            a = p.get("active", [])
            return a[0].get("maxHp", 0) if a else 0
        def active_hp_pct(p):
            hp = active_hp(p); mhp = active_max_hp(p)
            return hp / mhp if mhp else 0.0
        def active_energy(p):
            a = p.get("active", [])
            return len(a[0].get("energies", [])) if a else 0
        def active_id(p):
            a = p.get("active", [])
            return a[0]["id"] if a else None

        return {
            "turn":               current.get("turn", 0),
            "my_index":           my_idx,
            "first_player":       current.get("firstPlayer", 0),
            "my_prizes":          prizes_taken(me),
            "opp_prizes":         prizes_taken(opp),
            "prize_lead":         prizes_taken(me) - prizes_taken(opp),
            "my_active_id":       active_id(me),
            "my_active_hp":       active_hp(me),
            "my_active_max_hp":   active_max_hp(me),
            "my_active_hp_pct":   active_hp_pct(me),
            "my_active_energy":   active_energy(me),
            "opp_active_id":      active_id(opp),
            "opp_active_hp":      active_hp(opp),
            "opp_active_max_hp":  active_max_hp(opp),
            "opp_active_hp_pct":  active_hp_pct(opp),
            "opp_active_energy":  active_energy(opp),
            "my_bench_count":     len(me.get("bench", [])),
            "opp_bench_count":    len(opp.get("bench", [])),
            "my_deck":            me.get("deckCount", 0),
            "opp_deck":           opp.get("deckCount", 0),
            "my_hand":            me.get("handCount", 0),
            "my_poisoned":        me.get("poisoned", False),
            "my_burned":          me.get("burned", False),
            "my_asleep":          me.get("asleep", False),
            "my_paralyzed":       me.get("paralyzed", False),
            "energy_attached":    current.get("energyAttached", False),
            "supporter_played":   current.get("supporterPlayed", False),
            "retreated":          current.get("retreated", False),
            "_me":                me,
            "_opp":               opp,
        }


# ── option type constants ─────────────────────────────────────────────────────

OPTION_TYPE = {
    0:  "MULLIGAN",
    1:  "COIN_FLIP_HEAD",
    2:  "COIN_FLIP_TAIL",
    3:  "SELECT_POKEMON",
    7:  "PLAY_CARD",
    8:  "PLACE_ON_BENCH",
    9:  "EVOLVE",
    12: "USE_ABILITY",
    13: "ATTACK",
    14: "END_TURN",
}


# ── deck utilities ────────────────────────────────────────────────────────────

def load_deck_csv(path: Path) -> list:
    with open(path, "r") as f:
        lines = f.read().strip().split("\n")
    return [int(lines[i]) for i in range(60)]


def save_deck_csv(deck: list, path: Path):
    with open(path, "w") as f:
        f.write("\n".join(str(c) for c in deck))
    print(f"[simulator] Deck saved to {path}")


def validate_deck(deck: list, cards: dict) -> tuple:
    from collections import Counter
    errors = []
    if len(deck) != 60:
        errors.append(f"Deck has {len(deck)} cards, needs 60")
    for card_id, count in Counter(deck).items():
        if count > 2:
            card = cards.get(str(card_id))
            name = card.name if card else str(card_id)
            errors.append(f"{name} appears {count}x (max 2)")
    basic_ids = {cid for cid, c in cards.items()
                 if c.is_pokemon() and c.is_basic()}
    if not any(str(c) in basic_ids for c in deck):
        errors.append("Deck has no Basic Pokémon")
    return (len(errors) == 0, errors)


# ── self-play runner ──────────────────────────────────────────────────────────

def run_game(deck0, deck1, agent0_fn=None, agent1_fn=None,
             max_turns=500, verbose=False) -> dict:
    """Run one complete game. agent_fn(obs_dict) -> list[int]"""
    sim = SimulatorWrapper(deck0, deck1)
    try:
        obs_dict = sim.reset()
        for turn in range(max_turns):
            if sim.done:
                break
            obs = to_observation_class(obs_dict)
            if obs.select is None or len(obs.select.option) == 0:
                break
            # choose action
            player   = sim.current_player()
            agent_fn = agent0_fn if player == 0 else agent1_fn
            try:
                action = agent_fn(obs_dict) if agent_fn else sim.safe_action()
            except Exception:
                action = sim.safe_action()
            obs_dict = sim.step(action)
            if verbose and turn % 10 == 0:
                print(f"  turn {turn} | player {player}")
    except Exception as e:
        sim.close()
        return {"winner": -1, "turns": sim.turns, "error": str(e)}
    sim.close()
    return {"winner": sim.result, "turns": sim.turns, "error": None}


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    deck_path = ROOT / "sample_submission" / "deck.csv"
    deck      = load_deck_csv(deck_path)
    print(f"[simulator] Deck: {len(deck)} cards | first 5: {deck[:5]}")

    print("\n[simulator] Running 3 test games (random vs random)...")
    for i in range(3):
        result = run_game(deck, deck, verbose=False)
        print(f"  Game {i+1}: Winner=Player {result['winner']} "
              f"Turns={result['turns']} Error={result['error']}")

    print("\n[simulator] Board state fields available to agent:")
    sim = SimulatorWrapper(deck, deck)
    sim.reset()
    action = sim.safe_action()
    sim.step(action)
    board = sim.get_board_state()
    for k, v in board.items():
        if not k.startswith("_"):
            print(f"  {k:25} = {v}")
    sim.close()
import os
import sys
import json
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sample_submission"))  # add this line

from cg.api import Observation, to_observation_class
from agent.rule_agent import RuleAgent

# ── load card knowledge base ──────────────────────────────────────────────────
def load_features() -> dict:
    paths = [
        ROOT / "knowledge" / "card_knowledge_base.json",
        Path("/kaggle_simulations/agent/knowledge/card_knowledge_base.json"),
    ]
    for p in paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            print(f"[main] Loaded {len(data)} card features from {p}")
            return data
    print("[main] Warning: card_knowledge_base.json not found — using empty features")
    return {}


# ── load deck ─────────────────────────────────────────────────────────────────
def read_deck_csv() -> list:
    paths = [
        ROOT / "deck.csv",
        Path("/kaggle_simulations/agent/deck.csv"),
        ROOT / "data" / "my_deck.csv",
    ]
    for p in paths:
        if p.exists():
            with open(p, "r") as f:
                lines = f.read().strip().split("\n")
            deck = [int(lines[i]) for i in range(60)]
            print(f"[main] Loaded deck ({len(deck)} cards) from {p}")
            return deck
    raise FileNotFoundError("deck.csv not found")


# ── initialise agent (once at module load) ────────────────────────────────────
print("[main] Initialising agent...")
_deck     = read_deck_csv()
_features = load_features()
_agent    = RuleAgent(_deck, _features, verbose=False)
print("[main] Agent ready.")


# ── Kaggle submission entry point ─────────────────────────────────────────────
def agent(obs_dict: dict) -> list:
    """
    Pokémon TCG AI Agent — Kaggle submission entry point.

    On deck selection (obs.select is None):
        Returns list of 60 card IDs.

    On game decisions:
        Returns list of option indices satisfying
        minCount <= len(result) <= maxCount
        with no duplicate elements.
    """
    return _agent.act(obs_dict)


# ── local test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import random
    from environment.simulator_wrapper import SimulatorWrapper, run_game
    from cg.api import to_observation_class

    print("\n[main] Running local test — Rule agent vs Random agent (5 games)")
    print("─" * 60)

    def random_agent(obs_dict):
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return _deck
        n        = len(obs.select.option)
        minCount = obs.select.minCount
        if n == 0:      return []
        if minCount == 0: return []
        return random.sample(list(range(n)), min(minCount, n))

    rule_wins   = 0
    random_wins = 0

    for i in range(5):
        if i % 2 == 0:
            r = run_game(_deck, _deck, agent, random_agent)
            if r["winner"] == 0: rule_wins += 1
            else: random_wins += 1
            side = "Rule=P0"
        else:
            r = run_game(_deck, _deck, random_agent, agent)
            if r["winner"] == 1: rule_wins += 1
            else: random_wins += 1
            side = "Rule=P1"

        print(f"  Game {i+1} [{side}]: "
              f"Winner=P{r['winner']} "
              f"Turns={r['turns']:3d} "
              f"Err={r['error']}")

    print(f"\n  Rule wins  : {rule_wins}/5")
    print(f"  Random wins: {random_wins}/5")
    print("─" * 60)
    print("\n[main] To submit to Kaggle:")
    print("  1. Copy deck.csv + main.py + agent/ + knowledge/ + cg/ to submission folder")
    print("  2. Zip and upload via 'Submit Agent' button on competition page")
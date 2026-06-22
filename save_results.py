import json
from pathlib import Path

results = {
    "experiment": "Rule agent vs Random agent baseline",
    "deck": "Regigigas/Snorlax/Kyogre aggro",
    "games_per_condition": 20,
    "findings": {
        "random_vs_random":    {"p0_wins": 20, "p1_wins": 0, "avg_turns": 183.2},
        "rule_p0_vs_random_p1":{"p0_wins": 20, "p1_wins": 0, "avg_turns": 135.2},
        "random_p0_vs_rule_p1":{"p0_wins": 19, "p1_wins": 1, "avg_turns": 99.0},
    },
    "insights": [
        "First-player advantage dominates all matchups",
        "Rule agent wins 48 turns faster as P0 vs random P0",
        "Rule agent as P1 achieves 1 win vs 0 for random P1",
        "Average game length reduced by 84 turns with rule agent",
        "Deck needs going-second strategy to overcome first-player bias"
    ]
}

out = Path('reports/tables/baseline_results.json')
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, 'w') as f:
    json.dump(results, f, indent=2)
print(f'Saved to {out}')

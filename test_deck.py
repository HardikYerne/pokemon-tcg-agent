import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
import json, random
from pathlib import Path
from cg.api import to_observation_class
from environment.simulator_wrapper import load_deck_csv, run_game
from agent.rule_agent import make_agent

# load our balanced deck
deck = load_deck_csv(Path('data/my_deck.csv'))
print(f"Deck loaded: {len(deck)} cards")

# load features
with open('knowledge/card_knowledge_base.json', encoding='utf-8') as f:
    features = json.load(f)

# create agents
rule_agent = make_agent(deck, features)

def random_agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None: return deck
    n = len(obs.select.option)
    minCount = obs.select.minCount
    if n == 0: return []
    if minCount == 0: return []
    return random.sample(list(range(n)), min(minCount, n))

# run 20 games alternating sides
print('\nRule agent vs Random — 20 games')
print('-' * 50)
rule_wins = 0
random_wins = 0
total_turns = 0

for i in range(20):
    if i % 2 == 0:
        r = run_game(deck, deck, rule_agent, random_agent)
        if r['winner'] == 0: rule_wins += 1
        elif r['winner'] == 1: random_wins += 1
    else:
        r = run_game(deck, deck, random_agent, rule_agent)
        if r['winner'] == 1: rule_wins += 1
        elif r['winner'] == 0: random_wins += 1
    total_turns += r['turns']
    print(f"  Game {i+1:2d}: Winner=P{r['winner']} Turns={r['turns']:3d} Err={r['error']}")

print(f'\nRule wins  : {rule_wins}/20 ({rule_wins*5}%)')
print(f'Random wins: {random_wins}/20 ({random_wins*5}%)')
print(f'Avg turns  : {total_turns/20:.1f}')

import sys, json, random
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from environment.simulator_wrapper import load_deck_csv, run_game
from agent.rule_agent import make_agent
from pathlib import Path

deck = load_deck_csv(Path('data/my_deck.csv'))
with open('knowledge/card_knowledge_base.json', encoding='utf-8') as f:
    features = json.load(f)

rule_agent = make_agent(deck, features)

def random_agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None: return deck
    n = len(obs.select.option)
    minCount = obs.select.minCount
    if n == 0: return []
    if minCount == 0: return []
    return random.sample(list(range(n)), min(minCount, n))

# test 1: random vs random (baseline)
print('=== Random vs Random (20 games) ===')
p0_wins = p1_wins = 0
turns_list = []
for i in range(20):
    r = run_game(deck, deck, random_agent, random_agent)
    if r['winner'] == 0: p0_wins += 1
    elif r['winner'] == 1: p1_wins += 1
    turns_list.append(r['turns'])
print(f'  P0 wins: {p0_wins} | P1 wins: {p1_wins} | Avg turns: {sum(turns_list)/len(turns_list):.1f}')

# test 2: rule as P0 vs random as P1
print('\n=== Rule(P0) vs Random(P1) (20 games) ===')
p0_wins = p1_wins = 0
turns_list = []
for i in range(20):
    r = run_game(deck, deck, rule_agent, random_agent)
    if r['winner'] == 0: p0_wins += 1
    elif r['winner'] == 1: p1_wins += 1
    turns_list.append(r['turns'])
print(f'  Rule(P0) wins: {p0_wins} | Random(P1) wins: {p1_wins} | Avg turns: {sum(turns_list)/len(turns_list):.1f}')

# test 3: random as P0 vs rule as P1
print('\n=== Random(P0) vs Rule(P1) (20 games) ===')
p0_wins = p1_wins = 0
turns_list = []
for i in range(20):
    r = run_game(deck, deck, random_agent, rule_agent)
    if r['winner'] == 0: p0_wins += 1
    elif r['winner'] == 1: p1_wins += 1
    turns_list.append(r['turns'])
print(f'  Random(P0) wins: {p0_wins} | Rule(P1) wins: {p1_wins} | Avg turns: {sum(turns_list)/len(turns_list):.1f}')

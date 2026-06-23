import sys, json, random
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from cg.sim import lib
from environment.simulator_wrapper import load_deck_csv, run_game
from agent.rule_agent import make_agent as make_v1
from agent.rule_agent_v2 import make_agent as make_v2
from pathlib import Path

deck = load_deck_csv(Path('deck.csv'))
with open('knowledge/card_knowledge_base.json') as f:
    features = json.load(f)
atk_db = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}

v1 = make_v1(deck, features)
v2 = make_v2(deck, features, atk_db)

print('V2 vs V1 — 40 games (alternating sides)')
print('-'*50)
v2_wins = v1_wins = 0
turns_list = []

for i in range(40):
    if i % 2 == 0:
        r = run_game(deck, deck, v2, v1)
        if r['winner'] == 0: v2_wins += 1
        else: v1_wins += 1
    else:
        r = run_game(deck, deck, v1, v2)
        if r['winner'] == 1: v2_wins += 1
        else: v1_wins += 1
    turns_list.append(r['turns'])

print(f'V2 wins: {v2_wins}/40 ({v2_wins/40*100:.0f}%)')
print(f'V1 wins: {v1_wins}/40 ({v1_wins/40*100:.0f}%)')
print(f'Avg turns: {sum(turns_list)/len(turns_list):.1f}')

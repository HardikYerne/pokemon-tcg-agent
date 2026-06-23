import sys, json, random
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from environment.simulator_wrapper import load_deck_csv, run_game
from agent.rule_agent import make_agent
from pathlib import Path

deck = load_deck_csv(Path('deck.csv'))
with open('knowledge/card_knowledge_base.json') as f:
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

wins = losses = 0
for i in range(100):
    if i % 2 == 0:
        r = run_game(deck, deck, rule_agent, random_agent)
        if r['winner'] == 0: wins += 1
        else: losses += 1
    else:
        r = run_game(deck, deck, random_agent, rule_agent)
        if r['winner'] == 1: wins += 1
        else: losses += 1
    if (i+1) % 10 == 0:
        print(f'  {i+1}/100 wins:{wins} rate:{wins/(i+1)*100:.1f}%')

print(f'Final: {wins}/100 ({wins}% win rate vs random)')

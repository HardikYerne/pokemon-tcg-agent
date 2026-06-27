import sys, json, random
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from cg.sim import lib
from environment.simulator_wrapper import load_deck_csv, run_game, SimulatorWrapper
from agent.rule_agent import make_agent
from pathlib import Path
from collections import Counter

deck = load_deck_csv(Path('deck.csv'))
with open('knowledge/card_knowledge_base.json') as f:
    features = json.load(f)
atk_db = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}
agent = make_agent(deck, features, atk_db)

def random_agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None: return deck
    n = len(obs.select.option)
    minCount = obs.select.minCount
    if n == 0: return []
    if minCount == 0: return []
    return random.sample(list(range(n)), min(minCount, n))

def measure(name, agent0, agent1, games=20):
    p0w = p1w = turns_total = attacks_total = 0
    for i in range(games):
        sim = SimulatorWrapper(deck, deck)
        obs_dict = sim.reset()
        atk_count = 0
        while not sim.done:
            obs = to_observation_class(obs_dict)
            if obs.select is None or len(obs.select.option) == 0: break
            player = sim.current_player()
            fn = agent0 if player == 0 else agent1
            try:
                action = fn(obs_dict)
            except:
                action = sim.safe_action()
            if action and obs.select:
                if obs.select.option[action[0]].type == 13:
                    atk_count += 1
            obs_dict = sim.step(action)
        sim.close()
        if sim.result == 0: p0w += 1
        elif sim.result == 1: p1w += 1
        turns_total += sim.turns
        attacks_total += atk_count
    print(f'\n{name}')
    print(f'  P0 wins   : {p0w}/{games}')
    print(f'  P1 wins   : {p1w}/{games}')
    print(f'  Avg turns : {turns_total/games:.1f}')
    print(f'  Avg atks  : {attacks_total/games:.1f}')

print('='*50)
print('BASELINE MEASUREMENTS')
print('='*50)

measure('Random vs Random', random_agent, random_agent)
measure('Agent(P0) vs Random(P1)', agent, random_agent)
measure('Random(P0) vs Agent(P1)', random_agent, agent)
measure('Agent vs Agent', agent, agent)
import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from environment.simulator_wrapper import SimulatorWrapper, load_deck_csv
from agent.rule_agent import make_agent
from cg.sim import lib
from pathlib import Path
from collections import Counter

deck = load_deck_csv(Path('deck.csv'))
with open('knowledge/card_knowledge_base.json') as f:
    features = json.load(f)
atk_db = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}
agent = make_agent(deck, features, atk_db)

sim = SimulatorWrapper(deck, deck)
obs_dict = sim.reset()
action_log = []

for i in range(200):
    if sim.done: break
    obs = to_observation_class(obs_dict)
    if obs.select is None or len(obs.select.option) == 0: break
    types = [o.type for o in obs.select.option]
    action = agent(obs_dict)
    if action:
        chosen = obs.select.option[action[0]].type
        name = {0:'MULLIGAN',3:'SELECT',7:'PLAY',8:'BENCH',9:'EVOLVE',12:'ABILITY',13:'ATTACK',14:'END'}.get(chosen,'?')
        action_log.append(name)
    obs_dict = sim.step(action)

sim.close()
print(f'Winner:P{sim.result} Turns:{sim.turns}')
print('Actions:', Counter(action_log))

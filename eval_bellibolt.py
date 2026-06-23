import sys, json, random
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from cg.sim import lib
from environment.simulator_wrapper import load_deck_csv, run_game, SimulatorWrapper
from agent.rule_agent import make_agent
from pathlib import Path

deck = load_deck_csv(Path('deck.csv'))
with open('knowledge/card_knowledge_base.json') as f:
    features = json.load(f)
atk_db = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}
agent = make_agent(deck, features, atk_db)

# measure attacks per game
def count_attacks(agent_fn):
    sim = SimulatorWrapper(deck, deck)
    obs_dict = sim.reset()
    attacks = 0
    while not sim.done:
        obs = to_observation_class(obs_dict)
        if obs.select is None or len(obs.select.option) == 0: break
        action = agent_fn(obs_dict)
        if action and obs.select:
            if obs.select.option[action[0]].type == 13:
                attacks += 1
        obs_dict = sim.step(action)
    sim.close()
    return sim.result, sim.turns, attacks

print('Bellibolt deck — 10 games stats:')
total_turns = total_attacks = 0
for i in range(10):
    w, t, a = count_attacks(agent)
    total_turns += t
    total_attacks += a
    print(f'  Game {i+1}: W=P{w} Turns={t:3d} Attacks={a}')
print(f'\nAvg turns: {total_turns/10:.1f}  Avg attacks: {total_attacks/10:.1f}')

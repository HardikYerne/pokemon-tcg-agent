import sys, json, random
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from cg.sim import lib
from environment.simulator_wrapper import SimulatorWrapper, load_deck_csv
from agent.rule_agent import make_agent
from pathlib import Path

deck = load_deck_csv(Path('deck.csv'))
with open('knowledge/card_knowledge_base.json') as f:
    features = json.load(f)

attacks_data = json.loads(lib.AllAttack().decode())
atk_map = {a['attackId']: a for a in attacks_data}

rule_bot = make_agent(deck, features)

def count_game(agent0_fn, agent1_fn):
    sim = SimulatorWrapper(deck, deck)
    obs_dict = sim.reset()
    attacks0 = attacks1 = 0
    while not sim.done:
        obs = to_observation_class(obs_dict)
        if obs.select is None or len(obs.select.option) == 0:
            break
        player = sim.current_player()
        fn = agent0_fn if player == 0 else agent1_fn
        try:
            action = fn(obs_dict)
        except:
            action = sim.safe_action()
        # count attacks
        if action and obs.select:
            chosen = obs.select.option[action[0]]
            if chosen.type == 13:
                if player == 0: attacks0 += 1
                else: attacks1 += 1
        obs_dict = sim.step(action)
    sim.close()
    return sim.result, sim.turns, attacks0, attacks1

def random_fn(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None: return deck
    n = len(obs.select.option)
    minCount = obs.select.minCount
    if n == 0: return []
    if minCount == 0: return []
    return random.sample(list(range(n)), min(minCount, n))

print('Rule(P0) vs Random(P1) — 20 games')
print(f'{"Winner":8} {"Turns":6} {"Atk0":6} {"Atk1":6}')
print('-'*30)
for i in range(20):
    w, t, a0, a1 = count_game(rule_bot, random_fn)
    print(f'  P{w}      {t:5d}  {a0:5d}  {a1:5d}')

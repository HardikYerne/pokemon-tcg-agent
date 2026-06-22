import sys, json, random
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from cg.sim import lib
from environment.simulator_wrapper import SimulatorWrapper, load_deck_csv
from pathlib import Path

all_attacks = json.loads(lib.AllAttack().decode())
atk_map = {a['attackId']: a for a in all_attacks}

deck = load_deck_csv(Path('data/my_deck.csv'))
sim  = SimulatorWrapper(deck, deck)
obs_dict = sim.reset()

attack_count = 0
endturn_count = 0
bench_count = 0
play_count = 0

for i in range(300):
    if sim.done:
        break
    obs = to_observation_class(obs_dict)
    if obs.select is None or len(obs.select.option) == 0:
        break

    types = [o.type for o in obs.select.option]

    # count action types chosen by safe_action
    action = sim.safe_action()
    if action:
        chosen_type = obs.select.option[action[0]].type
        if chosen_type == 13: attack_count += 1
        elif chosen_type == 14: endturn_count += 1
        elif chosen_type == 8: bench_count += 1
        elif chosen_type == 7: play_count += 1

    obs_dict = sim.step(action)

sim.close()
print(f'Game finished: Winner={sim.result} Turns={sim.turns}')
print(f'Action breakdown:')
print(f'  Attacks   : {attack_count}')
print(f'  End turn  : {endturn_count}')
print(f'  Bench     : {bench_count}')
print(f'  Play card : {play_count}')

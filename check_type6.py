import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from environment.simulator_wrapper import SimulatorWrapper, load_deck_csv
from pathlib import Path

deck = load_deck_csv(Path('deck.csv'))
sim = SimulatorWrapper(deck, deck)
obs_dict = sim.reset()

for i in range(200):
    if sim.done: break
    obs = to_observation_class(obs_dict)
    if obs.select is None or len(obs.select.option) == 0: break
    types = [o.type for o in obs.select.option]
    if 6 in types:
        print('Turn', i, 'found type 6!')
        for o in obs.select.option:
            print('  type:', o.type, 'area:', getattr(o,'area',None))
        break
    obs_dict = sim.step(sim.safe_action())

sim.close()
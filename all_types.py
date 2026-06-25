import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.api import to_observation_class
from environment.simulator_wrapper import SimulatorWrapper, load_deck_csv
from collections import Counter
from pathlib import Path
deck = load_deck_csv(Path('deck.csv'))
all_types = Counter()
for game in range(3):
    sim = SimulatorWrapper(deck, deck)
    obs_dict = sim.reset()
    for i in range(200):
        if sim.done: break
        obs = to_observation_class(obs_dict)
        if obs.select is None or len(obs.select.option)==0: break
        for o in obs.select.option: all_types[o.type] += 1
        obs_dict = sim.step(sim.safe_action())
    sim.close()
print(dict(sorted(all_types.items())))

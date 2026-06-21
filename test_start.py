import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from environment.simulator_wrapper import load_deck_csv
from pathlib import Path

# test sample deck first
sample = load_deck_csv(Path('sample_submission/deck.csv'))
print(f'Sample deck size: {len(sample)}')
obs, start = battle_start(sample, sample)
print(f'Sample deck result: obs={obs is not None} errorType={start.errorType}')
if obs: battle_finish()

# test our deck
our = load_deck_csv(Path('data/my_deck.csv'))
print(f'\nOur deck size: {len(our)}')
print(f'Our deck IDs: {sorted(set(our))}')
obs2, start2 = battle_start(our, our)
print(f'Our deck result: obs={obs2 is not None} errorType={start2.errorType}')
if obs2: battle_finish()

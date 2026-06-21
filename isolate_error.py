import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path

cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}

good_basics = [c['cardId'] for c in cards_data
               if c['basic'] and not c['ex'] and not c['megaEx']
               and c['attacks'] and c['hp'] >= 100][:6]

# test 1: basics + energy only
deck1 = good_basics[:4] * 3 + [3] * 48
obs, s = battle_start(deck1, deck1)
print(f'Test1 basics+energy: {obs is not None} err={s.errorType}')
if obs: battle_finish()

# test 2: add supporters only
supporters = [c['cardId'] for c in cards_data if c['cardType'] == 3]
deck2 = good_basics[:3]*2 + [3]*42 + [supporters[0]]*2 + [supporters[1]]*2 + [supporters[2]]*2 + [supporters[3]]*2 + [supporters[4]]*2 + [supporters[5]]*2
print(f'Deck2 size: {len(deck2)}')
obs2, s2 = battle_start(deck2, deck2)
print(f'Test2 with supporters: {obs2 is not None} err={s2.errorType}')
if obs2: battle_finish()

# test 3: add items only
items = [c['cardId'] for c in cards_data if c['cardType'] == 2]
deck3 = good_basics[:3]*2 + [3]*42 + [items[0]]*2 + [items[1]]*2 + [items[2]]*2 + [items[3]]*2 + [items[4]]*2 + [items[5]]*2
print(f'Deck3 size: {len(deck3)}')
obs3, s3 = battle_start(deck3, deck3)
print(f'Test3 with items: {obs3 is not None} err={s3.errorType}')
if obs3: battle_finish()

print(f'\nSupporter IDs tested: {supporters[:6]}')
print(f'Item IDs tested: {items[:6]}')

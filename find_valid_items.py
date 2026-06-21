import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib

cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}
items = [c['cardId'] for c in cards_data if c['cardType'] == 2]
print(f'Total items: {len(items)}')

good_basics = [c['cardId'] for c in cards_data
               if c['basic'] and not c['ex'] and not c['megaEx']
               and c['attacks'] and c['hp'] >= 100][:3]

# test each item individually
valid_items = []
for item_id in items:
    deck = good_basics * 4 + [3] * 44 + [item_id] * 4
    obs, s = battle_start(deck, deck)
    if obs:
        battle_finish()
        valid_items.append(item_id)
    
print(f'\nValid items: {len(valid_items)}/{len(items)}')
print('Valid item IDs and names:')
for cid in valid_items[:20]:
    print(f'  ID:{cid:5} | {valid[cid]["name"]}')

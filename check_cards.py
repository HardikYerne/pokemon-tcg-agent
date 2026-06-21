import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
import json
from cg.sim import lib

# get all valid card IDs from simulator
all_cards = lib.AllCard()
if all_cards:
    cards_data = json.loads(all_cards.decode())
    print(f'Simulator has {len(cards_data)} valid cards')
    print(f'First 5: {cards_data[:5]}')
    print(f'Type: {type(cards_data[0])}')
    
    # save valid IDs
    with open('data/valid_card_ids.json', 'w') as f:
        json.dump(cards_data, f)
    print('Saved to data/valid_card_ids.json')
else:
    print('AllCard returned nothing')

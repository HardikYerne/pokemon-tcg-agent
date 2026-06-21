import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path
from collections import Counter

cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}

# confirmed valid IDs
basics     = [251, 1072, 135, 721, 41, 61]   # non-ex basics HP>=100
supporters = [1181,1182,1183,1184,1185,1186]  # all valid
items      = [1154,1156,1157,1160,1161,1162,
              1163,1164,1166,1168]             # valid items only

deck = (
    # 12 Pokemon
    [basics[0]]*2 + [basics[1]]*2 + [basics[2]]*2 +
    [basics[3]]*2 + [basics[4]]*2 + [basics[5]]*2 +
    # 18 Energy
    [3]*18 +
    # 12 Supporters
    [supporters[0]]*2 + [supporters[1]]*2 + [supporters[2]]*2 +
    [supporters[3]]*2 + [supporters[4]]*2 + [supporters[5]]*2 +
    # 18 Items
    [items[0]]*2 + [items[1]]*2 + [items[2]]*2 +
    [items[3]]*2 + [items[4]]*2 + [items[5]]*2 +
    [items[6]]*2 + [items[7]]*2 + [items[8]]*2
)

print(f'Deck size: {len(deck)}')
assert len(deck) == 60

obs, s = battle_start(deck, deck)
print(f'Battle start: obs={obs is not None} errorType={s.errorType}')
if obs:
    battle_finish()
    Path('data/my_deck.csv').write_text('\n'.join(str(c) for c in deck))
    print('Saved to data/my_deck.csv!')
    print('\nDeck contents:')
    for cid, cnt in Counter(deck).most_common():
        print(f'  {cnt}x {valid[cid]["name"]:30} | HP:{valid[cid]["hp"]}')

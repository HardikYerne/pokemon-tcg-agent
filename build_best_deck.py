import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path
from collections import Counter

cards = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards}

deck = (
    [756]*2  +  # Mega Kangaskhan ex  CCC->200dmg  300HP tank
    [1002]*4 +  # Zangoose ex         CCC->180dmg  200HP
    [1010]*4 +  # Drampa              CCC->120dmg  130HP clean
    [234]*2  +  # Terapagos           CCC->100dmg  120HP clean
    [3]*18   +  # Water energy (colorless accepts any)
    [1181]*2 + [1182]*2 + [1183]*2 +
    [1184]*2 + [1185]*2 + [1186]*2 +
    [1154]*2 + [1156]*2 + [1157]*2 +
    [1160]*2 + [1161]*2 + [1162]*2 +
    [1163]*2 + [1164]*2 + [1166]*2
)

print(f'Deck size: {len(deck)}')
assert len(deck) == 60, f'Got {len(deck)}'

obs, s = battle_start(deck, deck)
print(f'Battle: obs={obs is not None} errorType={s.errorType}')
if obs:
    battle_finish()
    Path('deck.csv').write_text('\n'.join(str(c) for c in deck))
    Path('data/my_deck.csv').write_text('\n'.join(str(c) for c in deck))
    print('Saved!')
    for cid, cnt in Counter(deck).most_common():
        print(f'  {cnt}x {valid[cid]["name"]:30} HP:{valid[cid]["hp"]}')

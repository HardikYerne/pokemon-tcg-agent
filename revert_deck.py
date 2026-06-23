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
    [1002]*4 + [328]*4 + [1072]*2 +
    [4]*20 +
    [1181]*2 + [1182]*2 + [1183]*2 +
    [1184]*2 + [1185]*2 + [1186]*2 +
    [1154]*2 + [1156]*2 + [1157]*2 +
    [1160]*2 + [1161]*2 + [1162]*2 +
    [1163]*2 + [1164]*2 + [1166]*2
)

assert len(deck) == 60
obs, s = battle_start(deck, deck)
print('Battle:', obs is not None, 'err:', s.errorType)
if obs:
    battle_finish()
    Path('deck.csv').write_text('\n'.join(str(c) for c in deck))
    print('Saved! Zangoose/Pikachu deck restored')
    for cid, cnt in Counter(deck).most_common():
        name = valid[cid]['name']
        print(f'  {cnt}x {name}')

import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path
from collections import Counter

cards = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards}

# Hybrid deck:
# Cramorant (311): 1C->120dmg mid-game (opp has 3-4 prizes)
# Zangoose ex (1002): CCC->180dmg late game
# Pikachu ex (328): LLC->220dmg late game
# Water energy works as Colorless for all

deck = (
    [311]*4  +  # Hop's Cramorant  1C->120dmg
    [1002]*4 +  # Zangoose ex      CCC->180dmg
    [328]*2  +  # Pikachu ex       LLC->220dmg
    [3]*20   +  # Water energy (C for Cramorant, W for others)
    [1181]*2 + [1182]*2 + [1183]*2 +
    [1184]*2 + [1185]*2 + [1186]*2 +
    [1154]*2 + [1156]*2 + [1157]*2 +
    [1160]*2 + [1161]*2 + [1162]*2 +
    [1163]*2 + [1164]*2 + [1166]*2
)

print(f'Deck size: {len(deck)}')
assert len(deck) == 60

obs, s = battle_start(deck, deck)
print(f'Battle: obs={obs is not None} errorType={s.errorType}')
if obs:
    battle_finish()
    Path('deck.csv').write_text('\n'.join(str(c) for c in deck))
    Path('data/my_deck.csv').write_text('\n'.join(str(c) for c in deck))
    print('Saved!')
    for cid, cnt in Counter(deck).most_common():
        name = valid[cid]['name']
        hp = valid[cid]['hp']
        print(f'  {cnt}x {name:30} HP:{hp}')
import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path
from collections import Counter

cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}

# Fighting aggro deck
# Throh(531) 1F->120dmg, Sawk(602) 1F->90dmg, Solrock(676) 1F->70dmg
# + supporters + valid items + Fighting energy(6)

deck = (
    # Pokemon (12) — all 1-energy attackers
    [531]*4 +   # Throh      1F -> 120dmg
    [602]*4 +   # Sawk       1F -> 90dmg
    [676]*4 +   # Solrock    1F -> 70dmg
    # Energy (18) — Fighting only
    [6]*18 +
    # Supporters (12)
    [1181]*2 + [1182]*2 + [1183]*2 +
    [1184]*2 + [1185]*2 + [1186]*2 +
    # Items (18)
    [1154]*2 + [1156]*2 + [1157]*2 +
    [1160]*2 + [1161]*2 + [1162]*2 +
    [1163]*2 + [1164]*2 + [1166]*2
)

print(f'Deck size: {len(deck)}')
assert len(deck) == 60

obs, s = battle_start(deck, deck)
print(f'Battle start: obs={obs is not None} errorType={s.errorType}')
if obs:
    battle_finish()
    Path('deck.csv').write_text('\n'.join(str(c) for c in deck))
    Path('data/my_deck.csv').write_text('\n'.join(str(c) for c in deck))
    print('Saved!')
    for cid, cnt in Counter(deck).most_common():
        print(f'  {cnt}x {valid[cid]["name"]}')

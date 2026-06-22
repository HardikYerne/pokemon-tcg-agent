import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path
from collections import Counter

cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}

# best pokemon for our deck:
# Regigigas (251)  - colorless, 160HP, 100dmg
# Snorlax (1072)   - colorless, 160HP, 160dmg
# Kyogre (721)     - water,     150HP, 130dmg

deck = (
    # Pokemon (12)
    [251]*4 +    # Regigigas  - colorless attacker
    [1072]*4 +   # Snorlax    - colorless attacker
    [721]*4 +    # Kyogre     - water attacker
    # Energy (18) - water works for Kyogre, colorless accepts anything
    [3]*18 +     # Basic Water Energy
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
    Path('data/my_deck.csv').write_text('\n'.join(str(c) for c in deck))
    print('Saved!')
    print('\nDeck:')
    for cid, cnt in Counter(deck).most_common():
        print(f'  {cnt}x {valid[cid]["name"]}')

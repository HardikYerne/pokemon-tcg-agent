import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path
from collections import Counter

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}
valid = {c['cardId']: c for c in cards}

# find colorless basics with no self-damage and no discard
print('Best CCC basics no self-damage no discard:')
for c in cards:
    if not c['basic']: continue
    for aid in c['attacks']:
        a = attacks.get(aid, {})
        cost = a.get('energies', [])
        dmg  = a.get('damage', 0)
        text = a.get('text', '').lower()
        # all colorless cost
        if all(e == 0 for e in cost) and len(cost) <= 3 and dmg >= 100:
            bad = any(kw in text for kw in ['discard', 'damage to itself', 'flip'])
            print(f"  ID:{c['cardId']:5} {c['name']:25} HP:{c['hp']:4} "
                  f"Dmg:{dmg:4} Cost:{'C'*len(cost)} bad:{bad} | {text[:50]}")

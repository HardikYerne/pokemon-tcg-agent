import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}
valid = {c['cardId']: c for c in cards}

# Test every basic pokemon - find highest damage with lowest cost
print('All valid basics ranked by best attack:')
results = []
for c in cards:
    if not c['basic']:
        continue
    best_dmg = 0
    best_atk = None
    best_cost = 99
    for aid in c['attacks']:
        a = attacks.get(aid, {})
        dmg  = a.get('damage', 0)
        cost = len(a.get('energies', []))
        text = a.get('text', '').lower()
        bad  = any(kw in text for kw in ['flip', 'discard all', 'does nothing'])
        if dmg > best_dmg and not bad:
            best_dmg  = dmg
            best_atk  = a
            best_cost = cost
    if best_dmg >= 100:
        results.append((best_dmg, best_cost, c['cardId'],
                       c['name'], c['hp'], c['ex'], best_atk))

results.sort(key=lambda x: (-x[0], x[1]))
emap = {0:'C',1:'G',2:'R',3:'W',4:'L',5:'P',6:'F',7:'D',8:'M'}
print(f"{'Name':28} {'HP':5} {'EX':4} {'Dmg':5} {'Cost':8} {'Attack'}")
print('-'*75)
for dmg,cost,cid,name,hp,ex,atk in results[:30]:
    cs = ''.join(emap.get(e,'?') for e in atk['energies'])
    print(f"  {name:26} {hp:5} {'ex' if ex else '  ':4} "
          f"{dmg:5} {cs:8} {atk['name'][:20]}")
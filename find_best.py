import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}

# find basics — sort by damage/energy ratio, show all
print('Best basics by damage (no ex/mega):')
results = []
for c in cards:
    if not c['basic'] or c['ex'] or c['megaEx']:
        continue
    for aid in c['attacks']:
        a = attacks.get(aid, {})
        cost    = a.get('energies', [])
        dmg     = a.get('damage', 0)
        text    = a.get('text', '')
        n_cost  = len([e for e in cost if e != 0])  # non-colorless energy
        total   = len(cost)
        if dmg >= 80 and total <= 2:
            conditional = any(kw in text.lower() for kw in
                ['if ', 'unless', 'for each', 'does nothing'])
            results.append((dmg, total, c['cardId'], c['name'],
                            c['hp'], a['name'], cost, conditional, text[:60]))

results.sort(key=lambda x: (-x[0], x[1]))
print(f"{'Name':25} | {'HP':4} | {'Attack':20} | {'Dmg':4} | {'Cost':12} | {'Cond'}")
print('-'*90)
for dmg, tot, cid, name, hp, atk, cost, cond, text in results[:25]:
    print(f"  ID:{cid:5} {name:22} | {hp:4} | {atk:20} | {dmg:4} | {str(cost):12} | {'YES' if cond else 'no'} | {text[:40]}")

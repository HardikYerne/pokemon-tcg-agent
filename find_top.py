import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}

# find ALL basics including ex with best attack profiles
# ex give 2 prizes but hit harder — sometimes worth it
print('Best basics INCLUDING ex (top attackers by damage):')
results = []
for c in cards:
    if not c['basic']:
        continue
    for aid in c['attacks']:
        a    = attacks.get(aid, {})
        cost = a.get('energies', [])
        dmg  = a.get('damage', 0)
        text = a.get('text', '').lower()
        total = len(cost)
        if dmg >= 100 and total <= 3:
            conditional = any(kw in text for kw in
                ['if ', 'unless', 'does nothing', 'only if'])
            results.append((
                dmg, total, c['cardId'], c['name'], c['hp'],
                c['ex'], a['name'], cost, conditional, text[:50]
            ))

results.sort(key=lambda x: (-x[0], x[1]))
print(f"{'Name':28} {'HP':5} {'EX':4} {'Atk':22} {'Dmg':5} {'Cost':15} {'Cond'}")
print('-'*95)
for dmg,tot,cid,name,hp,ex,atk,cost,cond,text in results[:25]:
    emap = {0:'C',1:'G',2:'R',3:'W',4:'L',5:'P',6:'F',7:'D',8:'M'}
    cs = ''.join(emap.get(e,'?') for e in cost)
    print(f"  {cid:5} {name:25} {hp:5} {'ex' if ex else '  ':4} {atk:22} {dmg:5} {cs:15} {'YES' if cond else 'no'}")

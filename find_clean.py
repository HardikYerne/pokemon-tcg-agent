import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}

results = []
for c in cards:
    if not c['basic'] or c['ex'] or c['megaEx']:
        continue
    for aid in c['attacks']:
        a    = attacks.get(aid, {})
        cost = a.get('energies', [])
        dmg  = a.get('damage', 0)
        text = a.get('text', '').lower()
        total = len(cost)
        if dmg >= 60 and total <= 2:
            conditional = any(kw in text for kw in
                ['if ', 'unless', 'for each', 'does nothing',
                 'flip', 'coin', 'discard'])
            if not conditional:
                results.append((dmg, total, c['cardId'], c['name'],
                                c['hp'], a['name'], cost))

results.sort(key=lambda x: (-x[0], x[1]))
print(f"Unconditional basics (60+dmg, max 2 energy, no flip/discard):")
print(f"{'ID':6} {'Name':25} {'HP':5} {'Attack':22} {'Dmg':5} {'Cost'}")
print('-'*80)
for dmg, tot, cid, name, hp, atk, cost in results[:20]:
    emap = {0:'C',1:'G',2:'R',3:'W',4:'L',5:'P',6:'F',7:'D',8:'M'}
    cost_str = ''.join(emap.get(e,'?') for e in cost)
    print(f"  {cid:5} {name:25} {hp:5} {atk:22} {dmg:5} {cost_str}")

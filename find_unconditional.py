import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}

# find basics with unconditional single energy attacks
print('Unconditional single-energy basics:')
results = []
for c in cards:
    if not c['basic'] or c['ex'] or c['megaEx']:
        continue
    for aid in c['attacks']:
        a = attacks.get(aid, {})
        cost = a.get('energies', [])
        dmg  = a.get('damage', 0)
        text = a.get('text', '')
        # single energy = exactly 1 element in cost
        if len(cost) == 1 and dmg >= 60:
            # unconditional = no conditional text
            conditional = any(kw in text.lower() for kw in
                ['if ', 'unless', 'for each', 'does nothing', 'only if'])
            if not conditional:
                results.append((dmg, c['cardId'], c['name'],
                                c['hp'], a['name'], cost[0], text[:50]))

results.sort(reverse=True)
for dmg, cid, name, hp, atk, energy, text in results[:20]:
    etype = {1:'G',2:'R',3:'W',4:'L',5:'P',6:'F',7:'D',8:'M',0:'C'}.get(energy,'?')
    print(f"  ID:{cid:5} | {name:25} | HP:{hp:4} | {atk:20} | Dmg:{dmg:4} | {etype}")

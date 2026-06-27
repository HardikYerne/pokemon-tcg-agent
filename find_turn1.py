import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}

# Sirf 1 energy cost wale attacks jo 50+ damage karte hain
print('1-energy attackers (50+ dmg):')
results = []
for c in cards:
    if not c['basic']: continue
    for aid in c['attacks']:
        a = attacks.get(aid, {})
        cost = a.get('energies', [])
        dmg  = a.get('damage', 0)
        text = a.get('text', '').lower()
        # exactly 1 energy in cost
        if len(cost) == 1 and dmg >= 50:
            bad = 'flip' in text or 'discard' in text
            results.append((dmg, c['cardId'], c['name'],
                           c['hp'], c['ex'], a['name'], cost[0], bad, text[:50]))

results.sort(reverse=True)
emap = {0:'C',1:'G',2:'R',3:'W',4:'L',5:'P',6:'F',7:'D',8:'M'}
for dmg,cid,name,hp,ex,atk,e,bad,text in results[:20]:
    print(f"  ID:{cid:5} {name:25} HP:{hp:4} {'ex' if ex else '  '} "
          f"{atk:20} Dmg:{dmg:4} Cost:{emap.get(e,'?')} bad:{bad}")
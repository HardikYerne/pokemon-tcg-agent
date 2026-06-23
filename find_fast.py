import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards_data = json.loads(lib.AllCard().decode())
attacks_data = json.loads(lib.AllAttack().decode())
atk_map = {a['attackId']: a for a in attacks_data}

# find basics with 1-energy attacks doing 60+ damage
print('Fast 1-energy basics (60+ damage):')
results = []
for c in cards_data:
    if not c['basic'] or c['ex'] or c['megaEx']:
        continue
    for atk_id in c['attacks']:
        atk = atk_map.get(atk_id, {})
        cost = atk.get('energies', [])
        dmg  = atk.get('damage', 0)
        # 1 energy = cost has 1 non-zero element
        non_zero = [e for e in cost if e != 0]
        if len(non_zero) == 1 and dmg >= 60:
            results.append((dmg, c['cardId'], c['name'], c['hp'], atk['name'], cost))

results.sort(reverse=True)
for dmg, cid, name, hp, atk_name, cost in results[:20]:
    print(f"  ID:{cid:5} | {name:25} | HP:{hp:4} | {atk_name:20} | Dmg:{dmg:4} | Cost:{cost}")

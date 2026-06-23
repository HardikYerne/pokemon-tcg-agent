import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}
valid = {c['cardId']: c for c in cards}

# find basics with BOTH a cheap setup attack AND a strong main attack
print('Basics with 1-energy setup + strong main attack:')
results = []
for c in cards:
    if not c['basic'] or len(c['attacks']) < 2:
        continue
    atks = [attacks.get(aid,{}) for aid in c['attacks']]
    # find cheap attack (1 energy) and expensive attack (2+ energy, 100+ dmg)
    cheap = [a for a in atks if len(a.get('energies',[])) == 1]
    strong = [a for a in atks if a.get('damage',0) >= 100
              and len(a.get('energies',[])) >= 2]
    if cheap and strong:
        emap = {0:'C',1:'G',2:'R',3:'W',4:'L',5:'P',6:'F',7:'D',8:'M'}
        for ch in cheap:
            for st in strong:
                cst = ''.join(emap.get(e,'?') for e in ch['energies'])
                sst = ''.join(emap.get(e,'?') for e in st['energies'])
                results.append((st['damage'], c['cardId'], c['name'],
                                c['hp'], ch['name'], cst,
                                st['name'], sst, st['damage']))

results.sort(reverse=True)
for dmg,cid,name,hp,ch_name,ch_cost,st_name,st_cost,st_dmg in results[:15]:
    print(f"  ID:{cid:5} {name:25} HP:{hp:4} | "
          f"Setup:{ch_name[:15]}({ch_cost}) | "
          f"Main:{st_name[:15]}({st_cost})={st_dmg}")

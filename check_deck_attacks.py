import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}
valid = {c['cardId']: c for c in cards}

# check our deck pokemon
for cid in [531, 602, 676]:
    c = valid[cid]
    print(f"\n{c['name']} (ID:{cid}) HP:{c['hp']}")
    for aid in c['attacks']:
        a = attacks[aid]
        print(f"  {a['name']:25} | Dmg:{a['damage']:4} | Cost:{a['energies']} | {a['text'][:60]}")

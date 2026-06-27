import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())
attacks = {a['attackId']: a for a in json.loads(lib.AllAttack().decode())}
valid = {c['cardId']: c for c in cards}

# Check Cramorant full details
c = valid[311]
print(f"{c['name']} HP:{c['hp']} ex:{c['ex']}")
for aid in c['attacks']:
    a = attacks[aid]
    emap = {0:'C',1:'G',2:'R',3:'W',4:'L',5:'P',6:'F',7:'D',8:'M'}
    cost = ''.join(emap.get(e,'?') for e in a['energies'])
    print(f"  {a['name']:25} Dmg:{a['damage']:4} Cost:{cost}")
    print(f"  Text: {a['text']}")
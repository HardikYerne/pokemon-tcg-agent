import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards}

# check our trainer cards
our_trainers = [1181,1182,1183,1184,1185,1186,  # supporters
                1154,1156,1157,1160,1161,1162,
                1163,1164,1166]                   # items

print('Our trainer cards:')
for cid in our_trainers:
    c = valid[cid]
    # get rule text from card data
    print(f"  ID:{cid:5} | {c['name']:30} | type:{c['cardType']}")

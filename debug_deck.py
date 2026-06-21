import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from collections import Counter

# get all valid cards
cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}

our = [971,971,61,61,514,514,920,920,953,953,
       192,192,531,534,142,
       6,6,6,6,6,6,4,4,4,4,4,7,7,7,7,
       1182,1182,1185,1185,1187,1187,1181,1181,1186,1186,
       1079,1079,1082,1082,1083,1083,1084,1084,1078,1078,
       1081,1081,1077,1077,1080,1080,1085,1085,1086,1086]

counts = Counter(our)
print('Card counts:')
for cid, cnt in sorted(counts.items(), key=lambda x: -x[1]):
    name = valid.get(cid, {}).get('name', f'ID:{cid}')
    print(f'  {cnt}x {name}')

# test minimal deck — just basics + energy
print('\nTesting minimal deck...')
# 4 basics + 56 energy
minimal = [61]*4 + [6]*56
obs, s = battle_start(minimal, minimal)
print(f'4 basics + 56 energy: obs={obs is not None} err={s.errorType}')
if obs: battle_finish()

# try sample deck card IDs only
sample_ids = list(set([721,722,723,1158,3,1235,1227,1145]))
print(f'\nSample deck unique IDs: {sample_ids}')
print('Sample card info:')
for cid in sample_ids:
    c = valid.get(cid, {})
    print(f'  {cid}: {c.get("name","?")} basic={c.get("basic")} cardType={c.get("cardType")}')

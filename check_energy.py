import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path
from collections import Counter

cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}

# check what energy types our pokemon need
pokemon_ids = [251, 1072, 135, 721, 41, 61]
print('Pokemon energy requirements:')
for pid in pokemon_ids:
    c = valid[pid]
    attacks = c.get('attacks', [])
    for atk in attacks:
        cost = atk.get('cost', [])
        print(f"  {c['name']:25} | {atk.get('name','?'):20} | cost={cost} dmg={atk.get('damage',0)}")

# energy type mapping
# 1=G 2=R 3=W 4=L 5=P 6=F 7=D 8=M 9=C(colorless)
print('\nEnergy IDs: 1=Grass 2=Fire 3=Water 4=Lightning 5=Psychic 6=Fighting 7=Dark 8=Metal 9=Colorless')

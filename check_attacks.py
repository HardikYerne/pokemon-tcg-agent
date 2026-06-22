import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}

# get all attacks
all_attacks = json.loads(lib.AllAttack().decode())
attacks = {a['attackId']: a for a in all_attacks}
print(f'Total attacks: {len(attacks)}')
print(f'Sample attack structure:')
for aid in [1042, 1043, 67, 68, 35, 36, 347]:
    a = attacks.get(aid, {})
    print(f"  ID:{aid} | {a}")

# check pokemon types
print('\nPokemon types in our deck:')
for pid in [721, 61, 41, 251, 135, 1072]:
    c = valid[pid]
    atk_details = [attacks.get(a, {}) for a in c['attacks']]
    print(f"  {c['name']:25} | pokemonType:{c['pokemonType']} | attacks:{atk_details}")

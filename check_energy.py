import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}

# check raw attack structure for our pokemon
for pid in [721, 61, 41, 251]:
    c = valid[pid]
    print(f"\n{c['name']}:")
    print(f"  attacks: {c['attacks']}")
    print(f"  pokemonType: {c['pokemonType']}")

import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

cards = json.loads(lib.AllCard().decode())

# weakness patterns dhundho
print('Weakness examples:')
for c in cards[:50]:
    if c.get('weakness'):
        print(f"  {c['name']:25} type:{c['pokemonType']} weakness:{c['weakness']}")
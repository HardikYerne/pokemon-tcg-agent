import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib

cards_data = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards_data}

# find all valid basic pokemon
basics = [c for c in cards_data if c['basic'] == True]
print(f'Total basics: {len(basics)}')
for c in basics[:20]:
    atks = c.get('attacks', [])
    dmg = atks[0] if atks else 0
    print(f"  ID:{c['cardId']:5} | {c['name']:25} | HP:{c['hp']:4} | attacks:{len(atks)}")

# build deck from confirmed basics only
# use 4 basics + energy like sample deck
print('\nTesting different basic combos...')
test_basics = [c['cardId'] for c in basics if c['attacks']][:4]
print(f'Test basics: {test_basics}')

test_deck = test_basics * 4 + [3] * 44
print(f'Test deck size: {len(test_deck)}')
obs, s = battle_start(test_deck, test_deck)
print(f'Result: obs={obs is not None} err={s.errorType}')
if obs: battle_finish()

import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.sim import lib

# get all valid cards from simulator
cards_data = json.loads(lib.AllCard().decode())
valid_ids  = {c['cardId'] for c in cards_data}

# check our deck
our_deck = [971,971,61,61,514,514,920,920,953,953,
            192,192,531,534,142,
            6,6,6,6,6,6,4,4,4,4,4,7,7,7,7,
            1182,1182,1185,1185,1187,1187,1181,1181,1186,1186,
            1079,1079,1082,1082,1083,1083,1084,1084,1078,1078,
            1081,1081,1077,1077,1080,1080,1085,1085,1086,1086]

print(f'Deck size: {len(our_deck)}')
invalid = [c for c in our_deck if c not in valid_ids]
print(f'Invalid card IDs: {set(invalid)}')

# show valid basics with attacks
print('\nValid basic pokemon with attacks:')
basics = [c for c in cards_data
          if c['basic'] and c['attacks'] and c['hp'] >= 100]
basics.sort(key=lambda x: x['hp'], reverse=True)
for c in basics[:15]:
    atk = c['attacks'][0]
    print(f"  ID:{c['cardId']:5} | {c['name']:25} | HP:{c['hp']:4} | "
          f"Dmg:{atk.get('damage',0):4} | Cost:{len(atk.get('cost',[]))}")

# show valid trainers
print('\nValid supporters:')
supporters = [c for c in cards_data if c['cardType'] == 3]
for c in supporters[:10]:
    print(f"  ID:{c['cardId']:5} | {c['name']:25}")

print('\nValid items:')
items = [c for c in cards_data if c['cardType'] == 2]
for c in items[:10]:
    print(f"  ID:{c['cardId']:5} | {c['name']:25}")

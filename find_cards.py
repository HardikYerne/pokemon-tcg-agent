import sys
sys.path.insert(0, '.')
import json

with open('knowledge/card_knowledge_base.json', encoding='utf-8') as f:
    features = json.load(f)

# find good basics
basics = [(cid, cf) for cid, cf in features.items()
          if cf.get('category') == 'Pokemon'
          and cf.get('subtype') == 'Basic'
          and cf.get('attack_damage')
          and cf.get('attack_damage') >= 60
          and cf.get('hp', 0) >= 100
          and not cf.get('is_ex')]

basics.sort(key=lambda x: x[1].get('damage_per_energy', 0) or 0, reverse=True)
print('Top basic attackers:')
for cid, cf in basics[:15]:
    print(f"  ID:{cid:5} | {cf['name']:25} | HP:{cf['hp']:4} | Dmg:{cf['attack_damage']:4} | DPE:{cf['damage_per_energy']}")

supporters = [(cid, cf) for cid, cf in features.items() if cf.get('subtype') == 'Supporter']
print(f'\nSupporters: {len(supporters)}')
for cid, cf in supporters[:8]:
    print(f"  ID:{cid:5} | {cf['name']:25}")

items = [(cid, cf) for cid, cf in features.items() if cf.get('subtype') == 'Item']
print(f'\nItems: {len(items)}')
for cid, cf in items[:8]:
    print(f"  ID:{cid:5} | {cf['name']:25}")

energy = [(cid, cf) for cid, cf in features.items() if cf.get('category') == 'Energy']
print(f'\nEnergy cards:')
for cid, cf in energy[:10]:
    print(f"  ID:{cid:5} | {cf['name']:25}")
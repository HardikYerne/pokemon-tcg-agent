import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path
from collections import Counter

cards = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards}

# Bellibolt ex deck:
# Iono's Tadbulb (268) basic -> Iono's Bellibolt ex (269) stage1
# Backup: Zangoose ex (1002) CCC=180dmg for off-turns
# Energy: Lightning (4) for LLLC cost

deck = (
    [268]*4  +  # Iono's Tadbulb    basic (evolves into Bellibolt)
    [269]*4  +  # Iono's Bellibolt ex  LLLC=230dmg 280HP
    [1002]*2 +  # Zangoose ex       CCC=180dmg (off-turn attacker)
    [4]*20   +  # Lightning energy
    [1181]*2 + [1182]*2 + [1183]*2 +
    [1184]*2 + [1185]*2 + [1186]*2 +
    [1154]*2 + [1156]*2 + [1157]*2 +
    [1160]*2 + [1161]*2 + [1162]*2 +
    [1163]*2 + [1164]*2 + [1166]*2
)

print(f'Deck size: {len(deck)}')
assert len(deck) == 60

obs, s = battle_start(deck, deck)
print(f'Battle: obs={obs is not None} errorType={s.errorType}')
if obs:
    battle_finish()
    Path('deck.csv').write_text('\n'.join(str(c) for c in deck))
    Path('data/my_deck.csv').write_text('\n'.join(str(c) for c in deck))
    print('Saved!')
    for cid, cnt in Counter(deck).most_common():
        print(f'  {cnt}x {valid[cid]["name"]:30} HP:{valid[cid]["hp"]}')

import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'sample_submission')
from cg.game import battle_start, battle_finish
from cg.sim import lib
from pathlib import Path
from collections import Counter

cards = json.loads(lib.AllCard().decode())
valid = {c['cardId']: c for c in cards}

# Scyther(916) CC->60dmg, Okidogi(116) FF->70dmg, Tauros(819) FF->70dmg
# Use Fighting energy — works for Okidogi/Tauros AND colorless for Scyther
deck = (
    [916]*4 +   # Scyther      CC -> 60dmg  (any energy)
    [116]*4 +   # Okidogi      FF -> 70dmg
    [819]*4 +   # Paldean Tauros FF -> 70dmg
    [6]*18 +    # Fighting energy (works as colorless too)
    [1181]*2 + [1182]*2 + [1183]*2 +
    [1184]*2 + [1185]*2 + [1186]*2 +
    [1154]*2 + [1156]*2 + [1157]*2 +
    [1160]*2 + [1161]*2 + [1162]*2 +
    [1163]*2 + [1164]*2 + [1166]*2
)

print(f'Deck size: {len(deck)}')
obs, s = battle_start(deck, deck)
print(f'Battle start: obs={obs is not None} errorType={s.errorType}')
if obs:
    battle_finish()
    Path('deck.csv').write_text('\n'.join(str(c) for c in deck))
    Path('data/my_deck.csv').write_text('\n'.join(str(c) for c in deck))
    print('Saved!')
    for cid, cnt in Counter(deck).most_common():
        print(f'  {cnt}x {valid[cid]["name"]}')

import sys, json
sys.path.insert(0, '.')
from pathlib import Path

deck = (
    [971]*2 + [61]*2 + [514]*2 + [920]*2 + [953]*2 +
    [192]*2 + [531]*1 + [534]*1 + [142]*1 +
    [6]*6 + [4]*5 + [7]*4 +
    [1182]*2 + [1185]*2 + [1187]*2 + [1181]*2 + [1186]*2 +
    [1079]*2 + [1082]*2 + [1083]*2 + [1084]*2 + [1078]*2 +
    [1081]*2 + [1077]*2 + [1080]*2 + [1085]*2 + [1086]*2
)

print(f"Deck size: {len(deck)}")
Path('data/my_deck.csv').write_text('\n'.join(str(c) for c in deck))
print("Saved to data/my_deck.csv")
print(f"First 10: {deck[:10]}")

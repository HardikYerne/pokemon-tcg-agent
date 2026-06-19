# config.py
from pathlib import Path

# ── Paths ──────────────────────────────────────────
ROOT_DIR   = Path(__file__).parent
DATA_DIR   = ROOT_DIR / "data"
KNOW_DIR   = ROOT_DIR / "knowledge"
REPORT_DIR = ROOT_DIR / "reports"

# Kaggle downloads — exact filenames as downloaded
CSV_EN  = DATA_DIR / "EN_Card_Data.csv"
CSV_JP  = DATA_DIR / "JP_Card_Data.csv"        # optional
PDF_EN  = DATA_DIR / "Card_ID List_EN.pdf"
PDF_JP  = DATA_DIR / "Card_ID List_JP.pdf"     # optional

# Preprocessing outputs
KNOWLEDGE_BASE = KNOW_DIR / "card_knowledge_base.json"
IMAGES_DIR     = KNOW_DIR / "extracted_images"

# ── Agent settings ─────────────────────────────────
AGENT_TYPE  = "rule"
DECK_SIZE   = 60
MAX_BENCH   = 5
PRIZE_COUNT = 6

# ── MCTS settings ──────────────────────────────────
MCTS_SIMULATIONS = 200
MCTS_DEPTH       = 5
UCB_CONSTANT     = 1.41

# ── RL settings ────────────────────────────────────
LEARNING_RATE  = 3e-4
GAMMA          = 0.99
EPISODES       = 50_000
BATCH_SIZE     = 64

# ── Evaluation ─────────────────────────────────────
EVAL_GAMES = 500

if __name__ == "__main__":
    print("ROOT_DIR:", ROOT_DIR)
    print("CSV_EN:  ", CSV_EN)
    print("PDF_EN:  ", PDF_EN)
    print("CSV_EN exists?", CSV_EN.exists())
    print("PDF_EN exists?", PDF_EN.exists())
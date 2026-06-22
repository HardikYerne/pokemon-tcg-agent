import sys
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"

# ── style ─────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "#1a1a2e",
    "axes.facecolor":    "#16213e",
    "axes.edgecolor":    "#e94560",
    "axes.labelcolor":   "#eaeaea",
    "xtick.color":       "#eaeaea",
    "ytick.color":       "#eaeaea",
    "text.color":        "#eaeaea",
    "grid.color":        "#0f3460",
    "grid.linewidth":    0.8,
    "font.family":       "monospace",
    "axes.titlepad":     14,
})

COLORS = {
    "rule":   "#e94560",
    "random": "#0f3460",
    "accent": "#f5a623",
    "green":  "#2ecc71",
    "blue":   "#3498db",
    "purple": "#9b59b6",
}


# ── Chart 1: Win rate comparison bar chart ────────────────────────────────────
def chart_winrate():
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#1a1a2e")

    conditions = ["Random\nvs Random", "Rule(P0)\nvs Random(P1)", "Random(P0)\nvs Rule(P1)"]
    p0_wins    = [20, 20, 19]
    p1_wins    = [0,  0,  1]
    total      = 20

    x     = np.arange(len(conditions))
    width = 0.35

    bars0 = ax.bar(x - width/2, [w/total*100 for w in p0_wins],
                   width, label="Player 0 Win %",
                   color=COLORS["blue"], alpha=0.85, edgecolor="#eaeaea", linewidth=0.5)
    bars1 = ax.bar(x + width/2, [w/total*100 for w in p1_wins],
                   width, label="Player 1 Win %",
                   color=COLORS["rule"], alpha=0.85, edgecolor="#eaeaea", linewidth=0.5)

    # value labels
    for bar in bars0:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 1,
                f"{h:.0f}%", ha="center", va="bottom", fontsize=9)
    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 1,
                    f"{h:.0f}%", ha="center", va="bottom", fontsize=9)

    ax.set_xlabel("Matchup Condition", fontsize=11)
    ax.set_ylabel("Win Rate (%)", fontsize=11)
    ax.set_title("Win Rate by Agent Type & Position\n(20 games per condition)",
                 fontsize=13, fontweight="bold", color=COLORS["accent"])
    ax.set_xticks(x)
    ax.set_xticklabels(conditions, fontsize=10)
    ax.set_ylim(0, 115)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.4)

    # annotation
    ax.annotate("Rule agent achieves\nfirst P1 win →",
                xy=(2 + width/2, 5), xytext=(1.6, 30),
                fontsize=9, color=COLORS["accent"],
                arrowprops=dict(arrowstyle="->", color=COLORS["accent"]))

    plt.tight_layout()
    out = REPORTS / "charts" / "winrate_comparison.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[charts] Saved: {out}")


# ── Chart 2: Average turns per condition ─────────────────────────────────────
def chart_turns():
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#1a1a2e")

    conditions = ["Random vs\nRandom", "Rule(P0) vs\nRandom(P1)", "Random(P0) vs\nRule(P1)"]
    avg_turns  = [183.2, 135.2, 99.0]
    colors     = [COLORS["random"], COLORS["blue"], COLORS["rule"]]

    bars = ax.bar(conditions, avg_turns, color=colors,
                  alpha=0.85, edgecolor="#eaeaea", linewidth=0.5, width=0.5)

    for bar, val in zip(bars, avg_turns):
        ax.text(bar.get_x() + bar.get_width()/2, val + 2,
                f"{val:.1f}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    # improvement arrows
    ax.annotate("", xy=(1, avg_turns[1]), xytext=(0, avg_turns[0]),
                arrowprops=dict(arrowstyle="-|>", color=COLORS["green"], lw=2))
    ax.text(0.5, (avg_turns[0]+avg_turns[1])/2 + 5,
            f"−{avg_turns[0]-avg_turns[1]:.0f} turns",
            ha="center", fontsize=9, color=COLORS["green"])

    ax.annotate("", xy=(2, avg_turns[2]), xytext=(1, avg_turns[1]),
                arrowprops=dict(arrowstyle="-|>", color=COLORS["green"], lw=2))
    ax.text(1.5, (avg_turns[1]+avg_turns[2])/2 + 5,
            f"−{avg_turns[1]-avg_turns[2]:.0f} turns",
            ha="center", fontsize=9, color=COLORS["green"])

    ax.set_ylabel("Average Turns per Game", fontsize=11)
    ax.set_title("Game Length by Matchup Condition\n(Fewer turns = more decisive agent)",
                 fontsize=13, fontweight="bold", color=COLORS["accent"])
    ax.set_ylim(0, 220)
    ax.grid(axis="y", alpha=0.4)

    plt.tight_layout()
    out = REPORTS / "charts" / "avg_turns_comparison.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[charts] Saved: {out}")


# ── Chart 3: Deck composition pie chart ──────────────────────────────────────
def chart_deck():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    fig.patch.set_facecolor("#1a1a2e")

    # our deck
    labels1  = ["Pokémon\n(12)", "Energy\n(18)", "Supporters\n(12)", "Items\n(18)"]
    sizes1   = [12, 18, 12, 18]
    colors1  = [COLORS["rule"], COLORS["blue"], COLORS["purple"], COLORS["accent"]]
    explode1 = (0.05, 0.05, 0.05, 0.05)

    ax1.pie(sizes1, labels=labels1, colors=colors1, explode=explode1,
            autopct="%1.0f%%", startangle=90,
            textprops={"color": "#eaeaea", "fontsize": 11},
            wedgeprops={"edgecolor": "#1a1a2e", "linewidth": 2})
    ax1.set_title("Our Deck\n(Regigigas/Snorlax/Kyogre Aggro)",
                  fontsize=12, fontweight="bold", color=COLORS["accent"])

    # sample deck
    labels2  = ["Pokémon\n(10)", "Energy\n(35)", "Trainers\n(15)"]
    sizes2   = [10, 35, 15]
    colors2  = [COLORS["rule"], COLORS["blue"], COLORS["accent"]]
    explode2 = (0.05, 0.1, 0.05)

    ax2.pie(sizes2, labels=labels2, colors=colors2, explode=explode2,
            autopct="%1.0f%%", startangle=90,
            textprops={"color": "#eaeaea", "fontsize": 11},
            wedgeprops={"edgecolor": "#1a1a2e", "linewidth": 2})
    ax2.set_title("Sample Deck\n(Heavy Energy — Imbalanced)",
                  fontsize=12, fontweight="bold", color="#888888")

    fig.suptitle("Deck Composition Comparison",
                 fontsize=14, fontweight="bold", color="#eaeaea", y=1.02)

    plt.tight_layout()
    out = REPORTS / "figures" / "deck_composition.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[charts] Saved: {out}")


# ── Chart 4: Option type distribution (what decisions agents face) ────────────
def chart_action_types():
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#1a1a2e")

    action_types = ["Attack\n(13)", "End Turn\n(14)", "Bench\n(8)",
                    "Play Card\n(7)", "Select\n(3)", "Other"]
    counts       = [24, 34, 39, 26, 18, 19]
    colors       = [COLORS["rule"], COLORS["accent"], COLORS["blue"],
                    COLORS["purple"], COLORS["green"], "#888888"]

    bars = ax.barh(action_types, counts, color=colors,
                   alpha=0.85, edgecolor="#eaeaea", linewidth=0.5)

    for bar, val in zip(bars, counts):
        ax.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                str(val), va="center", fontsize=10)

    ax.set_xlabel("Count (in one game)", fontsize=11)
    ax.set_title("Decision Type Distribution\n(160-turn game sample)",
                 fontsize=13, fontweight="bold", color=COLORS["accent"])
    ax.grid(axis="x", alpha=0.4)
    ax.set_xlim(0, 50)

    plt.tight_layout()
    out = REPORTS / "figures" / "action_distribution.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[charts] Saved: {out}")


# ── Chart 5: Agent architecture diagram ──────────────────────────────────────
def chart_architecture():
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")

    def box(x, y, w, h, text, color, fontsize=10):
        rect = mpatches.FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle="round,pad=0.1",
            facecolor=color, edgecolor="#eaeaea",
            linewidth=1.5, alpha=0.9
        )
        ax.add_patch(rect)
        ax.text(x, y, text, ha="center", va="center",
                fontsize=fontsize, color="#eaeaea", fontweight="bold",
                wrap=True, multialignment="center")

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>",
                                   color="#eaeaea", lw=1.5))

    # data layer
    box(2, 7.2, 2.8, 0.7, "EN_Card_Data.csv", COLORS["blue"], 9)
    box(5, 7.2, 2.8, 0.7, "Card_ID_List_EN.pdf", COLORS["blue"], 9)
    box(8, 7.2, 2.8, 0.7, "Simulator (cg.dll)", COLORS["purple"], 9)

    # knowledge layer
    box(3.5, 5.8, 5.5, 0.7, "card_knowledge_base.json  (1267 cards + features)", COLORS["rule"], 9)
    arrow(2, 6.85, 3.0, 6.15)
    arrow(5, 6.85, 4.0, 6.15)

    # state layer
    box(3.5, 4.6, 5.5, 0.7, "SimulatorWrapper  →  get_board_state()", "#0f3460", 9)
    arrow(3.5, 5.45, 3.5, 4.95)
    arrow(8, 6.85, 6.5, 4.95)

    # strategy layer
    box(1.5, 3.3, 2.2, 0.7, "phase_detector", COLORS["accent"], 9)
    box(3.8, 3.3, 2.2, 0.7, "opponent_model", COLORS["accent"], 9)
    box(6.1, 3.3, 2.2, 0.7, "risk_analyzer", COLORS["accent"], 9)
    arrow(3.5, 4.25, 2.2, 3.65)
    arrow(3.5, 4.25, 3.8, 3.65)
    arrow(3.5, 4.25, 5.8, 3.65)

    # agent layer
    box(3.5, 2.1, 5.5, 0.7, "RuleAgent  →  Priority Decision Engine", COLORS["rule"], 10)
    arrow(1.5, 2.95, 2.5, 2.45)
    arrow(3.8, 2.95, 3.5, 2.45)
    arrow(6.1, 2.95, 4.8, 2.45)

    # output
    box(3.5, 0.9, 5.5, 0.7, "action  →  list[int]  →  Kaggle Submission", COLORS["green"], 10)
    arrow(3.5, 1.75, 3.5, 1.25)

    ax.set_title("Pokémon TCG AI Agent Architecture",
                 fontsize=14, fontweight="bold",
                 color=COLORS["accent"], pad=10)

    plt.tight_layout()
    out = REPORTS / "figures" / "agent_architecture.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[charts] Saved: {out}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ensure output dirs exist
    (REPORTS / "charts").mkdir(parents=True, exist_ok=True)
    (REPORTS / "figures").mkdir(parents=True, exist_ok=True)

    print("[charts] Generating all charts...")
    chart_winrate()
    chart_turns()
    chart_deck()
    chart_action_types()
    chart_architecture()
    print("\n[charts] All done! Files saved to reports/")
    print("\nFiles generated:")
    for f in sorted(REPORTS.rglob("*.png")):
        print(f"  {f}")
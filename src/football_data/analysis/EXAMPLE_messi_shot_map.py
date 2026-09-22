from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Arc, Circle, Rectangle

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "output" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PLAYER = "Lionel Andrés Messi Cuccittini"

query = """
    SELECT
        e.location[1] AS x,
        e.location[2] AS y,
        COALESCE(e.shot.statsbomb_xg, 0) AS xg,
        e.shot.outcome.name AS outcome,
        m.competition.competition_name AS competition,
        m.season.season_name AS season,
        m.match_date AS match_date
    FROM events AS e
    JOIN matches AS m
        ON m.match_id = TRY_CAST(
            regexp_extract(
                e.filename,
                '([0-9]+)[.]json$',
                1
            ) AS BIGINT
        )
    WHERE e.type.name = 'Shot'
      AND e.player.name = ?
      AND e.location IS NOT NULL
"""

with duckdb.connect(str(DATABASE_PATH), read_only=True) as con:
    df = con.execute(query, [PLAYER]).fetchdf()

if df.empty:
    raise ValueError(
        f"No shots found for {PLAYER}. "
        "Check the exact player name in the database."
    )

goals = df["outcome"].eq("Goal")
non_goals = ~goals

fig, ax = plt.subplots(figsize=(14, 9))
fig.patch.set_facecolor("#101820")
ax.set_facecolor("#176b45")

pitch_line = "#f4f1de"

ax.set_xlim(0, 120)
ax.set_ylim(0, 80)
ax.set_aspect("equal")
ax.axis("off")

# Pitch outline
ax.add_patch(
    Rectangle(
        (0, 0),
        120,
        80,
        fill=False,
        edgecolor=pitch_line,
        linewidth=2,
    )
)

# Halfway line and centre circle
ax.plot([60, 60], [0, 80], color=pitch_line, linewidth=2)
ax.add_patch(
    Circle(
        (60, 40),
        9.15,
        fill=False,
        edgecolor=pitch_line,
        linewidth=2,
    )
)
ax.scatter(60, 40, color=pitch_line, s=12)

# Penalty areas
for x in [0, 102]:
    ax.add_patch(
        Rectangle(
            (x, 18),
            18,
            44,
            fill=False,
            edgecolor=pitch_line,
            linewidth=2,
        )
    )

# Six-yard boxes
for x in [0, 114]:
    ax.add_patch(
        Rectangle(
            (x, 30),
            6,
            20,
            fill=False,
            edgecolor=pitch_line,
            linewidth=2,
        )
    )

# Penalty spots
ax.scatter([12, 108], [40, 40], color=pitch_line, s=10)

# Penalty arcs
ax.add_patch(
    Arc(
        (12, 40),
        18.3,
        18.3,
        angle=0,
        theta1=310,
        theta2=50,
        color=pitch_line,
        linewidth=2,
    )
)
ax.add_patch(
    Arc(
        (108, 40),
        18.3,
        18.3,
        angle=0,
        theta1=130,
        theta2=230,
        color=pitch_line,
        linewidth=2,
    )
)

# xG colour scale
normalise = Normalize(
    vmin=0,
    vmax=max(0.5, df["xg"].quantile(0.98)),
)
colours = plt.cm.inferno(normalise(df["xg"]))

# Non-goal shots
ax.scatter(
    df.loc[non_goals, "x"],
    df.loc[non_goals, "y"],
    c=colours[non_goals],
    s=55,
    alpha=0.75,
    edgecolors="#f4f1de",
    linewidths=0.5,
)

# Goals
ax.scatter(
    df.loc[goals, "x"],
    df.loc[goals, "y"],
    c=colours[goals],
    s=190,
    marker="*",
    edgecolors="#ffd166",
    linewidths=1.2,
    zorder=5,
)

colourbar = fig.colorbar(
    plt.cm.ScalarMappable(norm=normalise, cmap="inferno"),
    ax=ax,
    fraction=0.025,
    pad=0.02,
)
colourbar.set_label("Expected goals (xG)", color="white")
colourbar.ax.yaxis.set_tick_params(color="white")
plt.setp(colourbar.ax.get_yticklabels(), color="white")

# Summary statistics
shot_count = len(df)
goal_count = int(goals.sum())
total_xg = df["xg"].sum()
conversion_rate = 100 * goal_count / shot_count

ax.set_title(
    f"{PLAYER} | Shot Map",
    loc="left",
    color="white",
    fontsize=24,
    fontweight="bold",
    pad=20,
)

ax.text(
    0,
    84,
    (
        f"{shot_count:,} shots   |   "
        f"{goal_count:,} goals   |   "
        f"{total_xg:.1f} total xG   |   "
        f"{conversion_rate:.1f}% conversion"
    ),
    color="#f4f1de",
    fontsize=12,
)

legend_items = [
    Line2D(
        [0],
        [0],
        marker="o",
        color="none",
        markerfacecolor="#d95f59",
        markeredgecolor="#f4f1de",
        markersize=8,
        label="Shot",
    ),
    Line2D(
        [0],
        [0],
        marker="*",
        color="none",
        markerfacecolor="#ffd166",
        markeredgecolor="#ffd166",
        markersize=13,
        label="Goal",
    ),
]

ax.legend(
    handles=legend_items,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.03),
    ncol=2,
    frameon=False,
    labelcolor="white",
)

output_path = OUTPUT_DIR / "lionel_messi_shot_map.png"
plt.savefig(
    output_path,
    dpi=220,
    bbox_inches="tight",
    facecolor=fig.get_facecolor(),
)
plt.show()

print(f"Saved chart to: {output_path}")
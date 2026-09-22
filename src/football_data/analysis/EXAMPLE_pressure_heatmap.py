from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Arc

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "output" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEAM = "Barcelona"
COMPETITION = "La Liga"
SEASON = "2015/2016"

query = """
    SELECT
        e.location[1] AS x,
        e.location[2] AS y
    FROM events AS e
    JOIN matches AS m
        ON m.match_id = TRY_CAST(
            regexp_extract(
                e.filename,
                '([0-9]+)[.]json$',
                1
            ) AS BIGINT
        )
    WHERE e.type.name = 'Pressure'
      AND e.team.name = ?
      AND m.competition.competition_name = ?
      AND m.season.season_name = ?
      AND e.location IS NOT NULL
"""

with duckdb.connect(str(DATABASE_PATH), read_only=True) as con:
    df = con.execute(
        query,
        [TEAM, COMPETITION, SEASON],
    ).fetchdf()

if df.empty:
    raise ValueError(
        f"No pressure events found for {TEAM}, "
        f"{COMPETITION}, {SEASON}"
    )

fig, ax = plt.subplots(figsize=(12, 8))

# Football pitch: StatsBomb coordinates are 120 by 80.
ax.set_facecolor("#176b3a")
ax.set_xlim(0, 120)
ax.set_ylim(0, 80)
ax.set_aspect("equal")

line_colour = "white"

# Outer boundary and halfway line
ax.add_patch(
    Rectangle(
        (0, 0),
        120,
        80,
        fill=False,
        edgecolor=line_colour,
        linewidth=2,
    )
)
ax.axvline(60, color=line_colour, linewidth=2)

# Centre circle
ax.add_patch(
    plt.Circle(
        (60, 40),
        9.15,
        fill=False,
        color=line_colour,
        linewidth=2,
    )
)

# Penalty areas
ax.add_patch(
    Rectangle(
        (0, 18),
        18,
        44,
        fill=False,
        edgecolor=line_colour,
        linewidth=2,
    )
)
ax.add_patch(
    Rectangle(
        (102, 18),
        18,
        44,
        fill=False,
        edgecolor=line_colour,
        linewidth=2,
    )
)

# Goal areas
ax.add_patch(
    Rectangle(
        (0, 30),
        6,
        20,
        fill=False,
        edgecolor=line_colour,
        linewidth=2,
    )
)
ax.add_patch(
    Rectangle(
        (114, 30),
        6,
        20,
        fill=False,
        edgecolor=line_colour,
        linewidth=2,
    )
)

# Pressure density
ax.hexbin(
    df["x"],
    df["y"],
    gridsize=25,
    cmap="magma",
    mincnt=1,
    alpha=0.85,
)

ax.set_title(
    f"{TEAM} pressure locations\n"
    f"{COMPETITION}, {SEASON} ({len(df):,} pressures)",
    fontsize=16,
    pad=15,
)
ax.set_xlabel("Pitch length")
ax.set_ylabel("Pitch width")

plt.tight_layout()

output_path = OUTPUT_DIR / "barcelona_pressure_heatmap.png"
plt.savefig(output_path, dpi=200, bbox_inches="tight")
plt.show()

print(f"Saved chart to: {output_path}")
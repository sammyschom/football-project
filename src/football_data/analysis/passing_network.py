# Using match_id = 267533 for now to test pipeline with a single match.
# Notes:
# the circle is the node and should represent the player
# lines are passes with thickness being number of passes
# circle position - average position of that player 

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Rectangle

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "output" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# select which match, and which team to make the passing network from
TEAM = "Barcelona"
MATCH_ID = 267533

# understanding this query: 
# the first subquery collects the match_id and all events from the events table,
# then we are simply filling in the columns we want related to passes, and 
query = """
WITH match_events AS (
    SELECT
        TRY_CAST(
            regexp_extract(filename, '([0-9]+)[.]json$', 1)
            AS BIGINT
        ) AS match_id,
        events.*
    FROM events
)
SELECT
    match_id,
    id AS event_id,
    index AS event_index,
    period,
    timestamp,
    minute,
    second,
    team.name AS team,
    player.name AS passer,
    pass.recipient.name AS recipient,

    location[1] AS start_x,
    location[2] AS start_y,
    pass.end_location[1] AS end_x,
    pass.end_location[2] AS end_y,

    pass.length,
    pass.angle,
    pass.height.name AS pass_height,
    pass.outcome.name AS pass_outcome,
    under_pressure
FROM match_events
WHERE match_id = ?
  AND team.name = ?
  AND type.name = 'Pass'
  AND pass.outcome.name IS NULL
  AND pass.recipient.name IS NOT NULL
  AND period = 1
ORDER BY event_index;
"""

with duckdb.connect(str(DATABASE_PATH), read_only=True) as con:
    passes_df = con.execute(query, [MATCH_ID, TEAM]).fetchdf()

if passes_df.empty:
    raise ValueError(f"No pass events found for match {MATCH_ID}")

print(f"Loaded {len(passes_df)} passes")
#print(passes_df.head())

#------------ FROM HERE WE MOVE TO PYTHON, PANDAS, MATPLOTLIB, ANALYSIS ETC.. --------
# with the data being passes_df...

# Keep one team for one passing network
team_name = TEAM
team_passes = passes_df.copy()

# One node per player: average location of their passes
nodes = (
    team_passes
    .groupby(["passer"], as_index=False)
    .agg(
        x=("start_x", "mean"),
        y=("start_y", "mean"),
        passes_made=("passer", "size"),
    )
)

# One edge per passer-recipient pair
edges = (
    team_passes
    .groupby(["passer", "recipient"], as_index=False)
    .size()
    .rename(columns={"size": "pass_count"})
)

# Only show meaningful connections
edges = edges[edges["pass_count"] >= 3]

from mplsoccer import Pitch

pitch = Pitch(
    pitch_type="statsbomb",
    pitch_color="#10231b",
    line_color="#d8e6dc",
)

fig, ax = pitch.draw(figsize=(12, 8))

# Draw connections first, so nodes remain visible
for edge in edges.itertuples():
    passer = nodes[nodes["passer"] == edge.passer].iloc[0]
    recipient = nodes[nodes["passer"] == edge.recipient].iloc[0]

    ax.plot(
        [passer.x, recipient.x],
        [passer.y, recipient.y],
        color="#f4c95d",
        linewidth=0.8 + edge.pass_count * 0.25,
        alpha=0.45,
        zorder=1,
    )

# Draw player nodes
node_sizes = 250 + nodes["passes_made"] * 12

pitch.scatter(
    nodes["x"],
    nodes["y"],
    s=node_sizes,
    color="#e85d4a",
    edgecolors="#ffffff",
    linewidth=1.5,
    alpha=0.95,
    ax=ax,
    zorder=2,
)

# Add player labels
for node in nodes.itertuples():
    ax.text(
        node.x,
        node.y,
        node.passer.split()[-1],
        ha="center",
        va="center",
        color="white",
        fontsize=8,
        zorder=3,
    )

ax.set_title(
    f"{team_name} Passing Network\nMatch {MATCH_ID}",
    color="white",
    fontsize=16,
    pad=20,
)

fig.savefig(
    OUTPUT_DIR / f"passing_network_{MATCH_ID}.png",
    dpi=300,
    bbox_inches="tight",
    facecolor="#10231b",
)
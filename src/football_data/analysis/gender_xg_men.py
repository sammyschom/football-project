#imports:
import duckdb
from mplsoccer import Pitch
from pathlib import Path 
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

# firstly, need to set up root and output directory, like before 
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "output" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)   

# now get the data from the duckdb database, like before
con = duckdb.connect(DATABASE_PATH)

df = con.execute(
    """
    SELECT
        e.shot.statsbomb_xg AS xg,
        e.location[1] AS x,
        e.location[2] AS y,
        m.match_date,
        m.home_team.home_team_name AS home_team,
        m.away_team.away_team_name AS away_team
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
      AND COALESCE(e.shot.type.name, '') NOT IN ('Penalty', 'Free Kick')
      AND m.competition.competition_name = ?
      AND m.season.season_name = ?
      AND e.location IS NOT NULL
    ORDER BY xg DESC
    """,
    ["FIFA World Cup", "2022"],
).df()

from mplsoccer import Pitch
pitch = Pitch(pitch_type = "statsbomb",pitch_color='grass', line_color='white', stripe=False)
fig, ax = pitch.draw()

bin_statistic = pitch.bin_statistic(
    df["x"],
    df["y"],
    values=df["xg"],
    statistic="mean",
    bins=(30, 16)
)

xg_norm = Normalize(vmin=0, vmax=0.6)

heatmap = pitch.heatmap(
    bin_statistic,
    ax=ax,
    cmap="coolwarm",
    norm=xg_norm,
    edgecolors=None,
    linewidth=0.5,
)

fig.colorbar(heatmap, ax=ax, label="xG")

ax.set_title("FIFA World Cup 2022: xG Shot Contour")
plt.show()


# Women's World Cup 2023
# FIFA World Cup    2022

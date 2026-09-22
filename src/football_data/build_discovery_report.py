from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd

# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # back to the project root

DATABASE_PATH = (
    PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
)

OUTPUT_DIR = PROJECT_ROOT / "output" / "discovery"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_PATH = OUTPUT_DIR / "statsbomb_discovery_report.html"


# --------------------------------------------------
# MY 'JUPYTER NOTEBOOK' STYLE SQL QUERIES
# Add new queries to this list as you go.
# --------------------------------------------------

queries = [

    {
        "title": "01 — Database tables",
        "purpose": (
            "List the tables currently available "
            "in the DuckDB database."
        ),
        "sql": """
            SELECT
                table_schema,
                table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN (
                'information_schema',
                'pg_catalog'
            )
            ORDER BY
                table_schema,
                table_name
        """
    },


    {
    "title": "02 — Matches by competition",
    "purpose": (
        "Count the total number of games available "
        "for each competition across all seasons."
    ),
    "sql": """
        SELECT
            m.competition.competition_id AS competition_id,
            m.competition.competition_name AS competition_name,
            COUNT(DISTINCT m.match_id) AS game_count
        FROM matches AS m
        GROUP BY
            m.competition.competition_id,
            m.competition.competition_name
        ORDER BY
            game_count DESC,
            competition_name
    """
},

    {
        "title": "03 — Database column inventory",
        "purpose": (
            "Explore the columns and data types "
            "available across the database."
        ),
        "sql": """
            SELECT
                table_name,
                ordinal_position,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema NOT IN (
                'information_schema',
                'pg_catalog'
            )
            ORDER BY
                table_name,
                ordinal_position
        """
    },

    {
            "title": "04 — Counts by competition AND season",
            "purpose": (
                "Count the number of games by competition and season."
                "available across the database."
            ),
            "sql": """
                SELECT
    competition.competition_name AS competition,
    season.season_name AS season,
    COUNT(DISTINCT match_id) AS matches,
    MIN(match_date) AS first_match,
    MAX(match_date) AS last_match
FROM matches
GROUP BY
    competition.competition_name,
    season.season_name
ORDER BY
    matches DESC,
    competition,
    season;
            """
        },

         {
    "title": "05 — Matching events to matches",
    "purpose": (
        "Match event files to their corresponding games "
        "and count events per competition and season."
    ),
    "sql": """
    WITH event_counts AS (
        SELECT
            TRY_CAST(
                regexp_extract(
                    filename,
                    '([0-9]+)[.]json$',
                    1
                ) AS BIGINT
            ) AS match_id,
            COUNT(*) AS events
        FROM events
        GROUP BY match_id
    )

    SELECT
        m.competition.competition_name AS competition,
        m.season.season_name AS season,
        COUNT(*) AS matches,
        COUNT(ec.match_id) AS matches_with_events,
        COALESCE(SUM(ec.events), 0) AS events,
        COALESCE(
            ROUND(
                SUM(ec.events) * 1.0
                / NULLIF(COUNT(ec.match_id), 0),
                0
            ),
            0
        ) AS events_per_match
    FROM matches AS m
    LEFT JOIN event_counts AS ec
        ON m.match_id = ec.match_id
    GROUP BY
        m.competition.competition_name,
        m.season.season_name
    ORDER BY
        events DESC,
        competition,
        season
"""
},

{
        "title": "06 — What event types?",
        "purpose": (
            "List the event types available in the events table."
        ),
        "sql": """
            SELECT
    type.name AS event_type,
    COUNT(*) AS event_count,
    COUNT(DISTINCT filename) AS match_files
FROM events
GROUP BY type.name
ORDER BY event_count DESC;
        """
    },

    {
    "title": "07 — Exploring shot and xG data",
    "purpose": (
        "Explore shot events and their associated xG values "
        "by competition and season."
    ),
    "sql": """
        SELECT
            m.competition.competition_name AS competition,
            m.season.season_name AS season,
            COUNT(e.id) AS shots,
            COUNT(e.shot.statsbomb_xg) AS shots_with_xg,
            ROUND(
                AVG(e.shot.statsbomb_xg),
                3
            ) AS mean_xg,
            ROUND(
                SUM(e.shot.statsbomb_xg),
                2
            ) AS total_xg
        FROM matches AS m
        JOIN events AS e
            ON m.match_id = TRY_CAST(
                regexp_extract(
                    e.filename,
                    '([0-9]+)[.]json$',
                    1
                ) AS BIGINT
            )
        WHERE e.type.name = 'Shot'
        GROUP BY
            m.competition.competition_name,
            m.season.season_name
        ORDER BY
            shots DESC,
            competition,
            season
    """
},

{
    "title": "08 — Validating missing or duplicated files",
    "purpose": (
        "Validate the presence of all expected files and identify any "
        "missing or duplicated files."
    ),
    "sql": """
        WITH event_files AS (
    SELECT
        TRY_CAST(
            regexp_extract(filename, '([0-9]+)[.]json$', 1)
            AS BIGINT
        ) AS match_id,
        filename,
        COUNT(*) AS event_count
    FROM events
    GROUP BY filename, match_id
)
SELECT
    COUNT(*) AS event_files,
    COUNT(DISTINCT match_id) AS distinct_match_ids,
    COUNT(*) FILTER (WHERE match_id IS NULL) AS files_without_match_id
FROM event_files;
    """
},

{
    "title": "09 — Fitting 360 into the picture",
    "purpose": (
        "Starting to look at how the 360 data fits into "
        " the overall picture of matches and events."
    ),
    "sql": """
    WITH matches_with_360 AS (
        SELECT
            TRY_CAST(
                regexp_extract(
                    file,
                    '([0-9]+)[.]json$',
                    1
                ) AS BIGINT
            ) AS match_id
        FROM glob('data/raw/statsbomb/three-sixty/*.json')
    )

    SELECT
        m.competition.competition_name AS competition,
        m.season.season_name AS season,
        COUNT(*) AS total_matches,
        COUNT(m360.match_id) AS matches_with_360,
        COUNT(*) - COUNT(m360.match_id) AS matches_without_360,
        ROUND(
            100.0 * COUNT(m360.match_id) / NULLIF(COUNT(*), 0),
            2
        ) AS percent_with_360
    FROM matches AS m
    LEFT JOIN matches_with_360 AS m360
        ON m.match_id = m360.match_id
    GROUP BY
        m.competition.competition_name,
        m.season.season_name
    ORDER BY
        matches_with_360 DESC,
        competition,
        season
"""
},

{
    "title": "10 — Match event timeline",
    "purpose": (
        "Show each event in match order, including the event type, "
        "teams, players, timing, location, possession, and detailed "
        "event-specific StatsBomb data."
    ),
    "sql": """
        SELECT
            TRY_CAST(
                regexp_extract(
                    e.filename,
                    '([0-9]+)[.]json$',
                    1
                ) AS BIGINT
            ) AS match_id,

            m.match_date,
            m.home_team.home_team_name AS home_team,
            m.away_team.away_team_name AS away_team,
            m.competition.competition_name AS competition,
            m.season.season_name AS season,

            e.id AS event_id,
            e.index AS event_index,
            e.period,
            e.timestamp,
            e.minute,
            e.second,

            e.type.name AS event_type,
            e.team.name AS team,
            e.player.name AS player,
            e.position.name AS position,

            e.possession,
            e.possession_team.name AS possession_team,

            e.location[1] AS location_x,
            e.location[2] AS location_y,
            e.duration,
            e.under_pressure,
            e.off_camera,
            e.out,

            e.pass.recipient.name AS pass_recipient,
            e.pass.end_location[1] AS pass_end_x,
            e.pass.end_location[2] AS pass_end_y,
            e.pass.length AS pass_length,
            e.pass.angle AS pass_angle,
            e.pass.height.name AS pass_height,
            e.pass.outcome.name AS pass_outcome,

            e.carry.end_location[1] AS carry_end_x,
            e.carry.end_location[2] AS carry_end_y,

            e.shot.statsbomb_xg AS shot_xg,
            e.shot.outcome.name AS shot_outcome,
            e.shot.body_part.name AS shot_body_part,
            e.shot.technique.name AS shot_technique,

            e.duel.type.name AS duel_type,
            e.duel.outcome.name AS duel_outcome,

            e.foul_committed.type.name AS foul_type,
            e.foul_committed.card.name AS foul_card,

            e.foul_won.defensive AS foul_won_defensive,
            e.foul_won.advantage AS foul_won_advantage,
            e.foul_won.penalty AS foul_won_penalty,

            e.substitution.replacement.name AS substitution_replacement,
            e.substitution.outcome.name AS substitution_outcome

        FROM events AS e
        LEFT JOIN matches AS m
            ON m.match_id = TRY_CAST(
                regexp_extract(
                    e.filename,
                    '([0-9]+)[.]json$',
                    1
                ) AS BIGINT
            )
        WHERE match_id = 267533
        ORDER BY
            match_id,
            e.period,
            e.minute,
            e.second,
            e.index
    """
},


]


# --------------------------------------------------
# BUILD REPORT
# --------------------------------------------------

con = duckdb.connect(str(DATABASE_PATH), read_only=True)

report_sections = []

try:
    for query in queries:

        print(f"Running: {query['title']}")

        try:
            # Execute query and retrieve ALL result rows
            df = con.execute(query["sql"]).fetchdf()

            # Save the individual result as CSV
            csv_name = (
                query["title"]
                .split("—")[0]
                .strip()
                .replace(" ", "_")
                + ".csv"
            )

            df.to_csv(
                OUTPUT_DIR / csv_name,
                index=False
            )

            # Create a formatted HTML table
            table_html = df.to_html(
                index=False,
                border=0,
                classes="data-table",
                escape=True
            )

            section_html = f"""
            <section class="report-section">

                <h2>{query['title']}</h2>

                <p class="purpose">
                    {query['purpose']}
                </p>

                <div class="metadata">
                    {len(df):,} rows ·
                    {len(df.columns):,} columns
                </div>

                <details>
                    <summary>View SQL query</summary>
                    <pre><code>{query['sql']}</code></pre>
                </details>

                <div class="table-container">
                    {table_html}
                </div>

            </section>
            """

            report_sections.append(section_html)

        except Exception as e:
            report_sections.append(
                f"""
                <section class="report-section">
                    <h2>{query['title']}</h2>
                    <p>Query failed: {str(e)}</p>
                </section>
                """
            )

finally:
    con.close()


# --------------------------------------------------
# HTML REPORT TEMPLATE
# --------------------------------------------------

html = f"""
<!DOCTYPE html>
<html lang="en">

<head>
<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>StatsBomb Data Discovery</title>

<style>

body {{
    font-family: Arial, sans-serif;
    background: #f4f6f9;
    color: #172033;
    margin: 0;
    padding: 0;
}}

header {{
    background: #152238;
    color: white;
    padding: 40px 6%;
}}

header h1 {{
    margin: 0 0 12px;
    font-size: 30px;
}}

header p {{
    color: #cbd5e1;
    margin: 0;
}}

main {{
    max-width: 1400px;
    margin: auto;
    padding: 30px 4%;
}}

.report-section {{
    background: white;
    padding: 28px;
    margin-bottom: 28px;
    border-radius: 12px;
    box-shadow: 0 2px 10px #0000000c;
}}

h2 {{
    margin-top: 0;
    color: #152238;
}}

.purpose {{
    color: #526176;
}}

.metadata {{
    font-size: 13px;
    color: #64748b;
    margin: 16px 0;
}}

.table-container {{
    overflow-x: auto;
    max-height: 650px;
    overflow-y: auto;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}}

.data-table {{
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
    white-space: nowrap;
}}

.data-table th {{
    background: #eaf0f7;
    color: #152238;
    text-align: left;
    position: sticky;
    top: 0;
    z-index: 1;
}}

.data-table th,
.data-table td {{
    padding: 10px 14px;
    border-bottom: 1px solid #e8edf3;
}}

.data-table tr:nth-child(even) {{
    background: #f8fafc;
}}

details {{
    margin: 16px 0;
}}

pre {{
    background: #152238;
    color: #e2e8f0;
    padding: 16px;
    overflow-x: auto;
    border-radius: 8px;
}}

footer {{
    color: #64748b;
    text-align: center;
    padding: 30px;
}}

</style>
</head>

<body>

<header>
    <h1>StatsBomb Open Data</h1>
    <p>Data Discovery & Coverage Report</p>
    <p>Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}</p>
</header>

<main>

    <section class="report-section">
        <h2>Report overview</h2>
        <p>
            This report consolidates the results of
            exploratory SQL queries against the
            StatsBomb DuckDB database.
        </p>
        <p>
            Queries included:
            {len(queries)}
        </p>
    </section>

    {''.join(report_sections)}

</main>

<footer>
    StatsBomb Open Data · SQL Discovery
</footer>

</body>
</html>
"""


# --------------------------------------------------
# SAVE REPORT
# --------------------------------------------------

REPORT_PATH.write_text(
    html,
    encoding="utf-8"
)

print()
print("Report generated successfully:")
print(REPORT_PATH)
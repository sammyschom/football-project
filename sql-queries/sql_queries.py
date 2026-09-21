from pathlib import Path
import pprint
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
con = duckdb.connect(str(DATABASE_PATH))

# put sql queries here between the """ and """ triple quotes
result = con.sql(
"""
SELECT
        competition.competition_name AS competition,
        COUNT(*) AS games
    FROM matches
    GROUP BY competition.competition_name
    ORDER BY games DESC

"""
)

result.show(max_rows=1000)



#----------------------------------------------------------
#----------------------------------------------------------
#----------------------------------------------------------
# some example queries: 

# give title for what this does...
''' 
SELECT
        competition.competition_name AS competition,
        COUNT(*) AS games
    FROM matches
    GROUP BY competition.competition_name
    ORDER BY games DESC
'''

#shows total number of events for Barcelona by event type
'''
SELECT
        type.name AS event_type,
        COUNT(*) AS total_events
    FROM events
    WHERE team.name = 'Barcelona'
    GROUP BY type.name
    ORDER BY total_events DESC
'''

#shows the database folders!
'''
SELECT
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY table_schema, table_name;
'''

# for specific heatmap xg query
'''
SELECT
    location[1] AS x,
    location[2] AS y,
    shot.statsbomb_xg AS xg,
    shot.outcome.name AS outcome,
    filename
FROM events
WHERE team.name = 'Barcelona'
  AND type.name = 'Shot'
  AND location IS NOT NULL
ORDER BY xg DESC;
'''


#query to get the percentage of matches with 360 data by league
'''
WITH matches_with_360 AS (
    SELECT
        TRY_CAST(
            regexp_extract(file, '([0-9]+)\.json$', 1)
            AS BIGINT
        ) AS match_id
    FROM glob('data/raw/statsbomb/three-sixty/*.json')
)

SELECT
    m.competition.competition_name AS league,
    COUNT(*) AS total_matches,
    COUNT(m360.match_id) AS matches_with_360,
    ROUND(
        100.0 * COUNT(m360.match_id) / COUNT(*),
        2
    ) AS percent_with_360
FROM matches AS m
LEFT JOIN matches_with_360 AS m360
    ON m.match_id = m360.match_id
GROUP BY m.competition.competition_name
ORDER BY matches_with_360 DESC;
'''


# a delve into how the 360 data works
'''
SELECT
    event_uuid,
    frame_data.teammate,
    frame_data.actor,
    frame_data.keeper,
    frame_data.location[1] AS x,
    frame_data.location[2] AS y
FROM read_json_auto(
    'data/raw/statsbomb/three-sixty/3764440.json'
) AS data
CROSS JOIN UNNEST(data.freeze_frame) AS frame(frame_data)
LIMIT 20;
'''
from pathlib import Path
import pprint
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
con = duckdb.connect(str(DATABASE_PATH))

# put sql queries here between the """ and """ triple quotes
result = con.sql("""

SELECT
        type.name AS event_type,
        COUNT(*) AS total_events
    FROM events
    WHERE team.name = 'Manchester United'
    GROUP BY type.name
    ORDER BY total_events DESC
   
""")

print(result)

# some example queries: 

''' SELECT
        competition.competition_name AS competition,
        COUNT(*) AS games
    FROM matches
    GROUP BY competition.competition_name
    ORDER BY games DESC
'''

'''
SELECT
        type.name AS event_type,
        COUNT(*) AS total_events
    FROM events
    WHERE team.name = 'Manchester United'
    GROUP BY type.name
    ORDER BY total_events DESC
'''
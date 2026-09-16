from pathlib import Path
import pprint
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
con = duckdb.connect(str(DATABASE_PATH))

# put sql queries here between the """ and """ triple quotes
result = con.sql("""


   
""")

print(result)


#----------------------------------------------------------
# some example queries: 

# give title for what this does...
''' SELECT
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
        type.name AS event_type,
        COUNT(*) AS total_events
    FROM events
    WHERE team.name = 'Barcelona'
    GROUP BY type.name
    ORDER BY total_events DESC
'''
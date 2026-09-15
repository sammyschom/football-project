from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
COMPETITIONS_PATH = (
    PROJECT_ROOT / "data" / "raw" / "statsbomb" / "competitions.json"
)

con = duckdb.connect(str(DATABASE_PATH))

con.execute(
    """
    CREATE TABLE IF NOT EXISTS competitions AS
    SELECT * FROM read_json_auto(?)
    """,
    [str(COMPETITIONS_PATH)],
)

result = con.execute("SELECT * FROM competitions LIMIT 5").fetchdf()
print(result)

con.close()


from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "statsbomb"

con = duckdb.connect(str(DATABASE_PATH))


def create_table(table_name: str, file_pattern: str) -> None:
    path = RAW_PATH / file_pattern

    con.execute(f"DROP TABLE IF EXISTS {table_name}")

    con.execute(
        f"""
        CREATE TABLE {table_name} AS
        SELECT *
        FROM read_json_auto(
            ?,
            union_by_name = true,
            filename = true
        )
        """,
        [str(path)],
    )


create_table("competitions", "competitions.json")
create_table("matches", "matches/**/*.json")
create_table("events", "events/**/*.json")
create_table("lineups", "lineups/**/*.json")

print("\nTables:")
print(
    con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        ORDER BY table_name
        """
    ).fetchdf()
)

for table in ["competitions", "matches", "events", "lineups"]:
    print(f"\n--- {table} ---")
    print(con.execute(f"SELECT COUNT(*) AS row_count FROM {table}").fetchdf())
    print(con.execute(f"DESCRIBE {table}").fetchdf())

con.close()
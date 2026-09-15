import duckdb

con = duckdb.connect('statsbomb.duckdb')

con.execute("""
    CREATE TABLE IF NOT EXISTS competitions AS
    SELECT * FROM read_json_auto('data/raw/statsbomb/competitions.json')
""")

result = con.execute("SELECT * FROM competitions LIMIT 5").fetchdf()
print(result)
# football-project

My on-going football project, on the topic of football, data, analytics, visualisation, defence, networks, ML,...

### Completed

- Downloaded and stored the StatsBomb open data in `data/raw/statsbomb`.
- Loaded competitions, matches, events, and lineups into
  `data/processed/statsbomb.duckdb`, as a duckdb file
- Explored the database using SQL (embedded in python script) in
  `sql-queries/sql_queries.py`.
- Built a stakeholder-focused discovery report containing approximately ten
  queries covering available competitions, seasons, matches, event counts,
  schemas, and event coverage. To understand the structure of the data, and what is available.
  - Inspected consecutive event sequences from individual matches to understand
  how the event data represents football actions over time.
- Generated the discovery report at:
  `output/discovery/statsbomb_discovery_report.html` (Reccomended: open in integrated browser)
- Created a simple, traditional passing network from DuckDB data using Python and Matplotlib,
  providing an initial visual check that event locations and filtering behaved
  as expected.
  
- Added a staging layer inside DuckDB.
- Built and validated `staging.events`, a flattened event table containing
  match identifiers, event ordering, timestamps, teams, players, locations,
  possession, pressure, pass, and carry fields.

### Next up
- Make the analytics layer inside DuckDB. Any table in this layer should be ready to be imported for pure python analysis, vis etc...
- AND FOLLOW THE PLAN ON PAPER!!
- good job so far:)

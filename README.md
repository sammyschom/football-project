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
  `output/discovery/statsbomb_discovery_report.html` (Reccomended: open in integrated browser) Report generated locally, as large and only sometimes useful html file.
- Created a simple, traditional passing network from DuckDB data using Python and Matplotlib,
  providing an initial visual check that event locations and filtering behaved
  as expected.
  
- Added a staging layer inside DuckDB.
- Built and validated `staging.events`, a flattened event table containing
  match identifiers, event ordering, timestamps, teams, players, locations,
  possession, pressure, pass, and carry fields.
- Added `analytics.intervention_passes`, a raw intervention-window dataset
  containing five opponent passes before and after each complete **pressure** (just pressure for now)
  intervention within the pressured possession. It retains defender identity,
  intervention timing, and match context alongside each pass. Each pass has a
  relative position from `-5` through `-1` or `+1` through `+5`.
  Interventions without five passes on both sides are excluded by design.

  This is the SQL/Python boundary: SQL decides which passes belong to an
  intervention; Python constructs `Gpre`, `Gpost`, network values, and
  disruption measures.

  Rebuild it with:
  `python3 src/football_data/features/build_intervention_passes.py`

  Created `main_analysis` which reads in the `analytics.intervention_passes` file, takes only passes with a passer AND receiver, 
  created the first edge connection, which is just a simple pass frequency. More edge metrics can be added in due course with `EDGE_BUILDER`, currently outputs each intervention as a row, and the number of connections, sum which is the total number of pass events (validates the `WINDOW_SIZE`), and the max number of those edges.


### Next up
- Load one intervention from `analytics.intervention_passes` in Python and
  construct its pre/post edge lists.
- Define and test one network value `V(G)` before adding alternative measures.
- Keep ML, SHAP, Bayesian analysis, and composite disruption measures after
  the network construction and validation steps.
- AND FOLLOW THE PLAN ON PAPER!!
- good job so far:)

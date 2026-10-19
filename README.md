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

- This is the SQL/Python boundary: SQL decides which passes belong to an
  intervention; Python constructs `Gpre`, `Gpost`, network values, and
  disruption measures.

- Rebuild it with:
  `python3 src/football_data/features/build_intervention_passes.py`

- Created `main_analysis` which reads in the `analytics.intervention_passes` file, takes   only passes with a passer AND receiver, created the first edge connection, which is just a simple pass frequency. More edge metrics can be added in due course with `EDGE_BUILDER`, currently outputs each intervention as a row, and: the number of connections, sum which is the total number of pass events (validates; should be the same as the `WINDOW_SIZE`), and the max number of those edges.

- `main_analysis` now takes whichever defensive intervention you have selected near the top of the file. Reads the intervention label from the config at the top of the file. The main is now streamlined with `METRIC_CONFIG`

- Can filter for competition with the commented code within `def load_intervention_passes`

- Code currently works:
it prints per-intervention pre/post disruption summaries for:
completion rate
forward progression
it plots average disruption for each metric

- The analysis writes one canonical modeling dataset to
  `output/analysis/modeling_dataset.csv`. It has one row per complete
  intervention and contains shared intervention metadata plus
  `completion_pre`, `completion_post`, `completion_D`,
  `forward_progression_pre`, `forward_progression_post`,
  `forward_progression_D`, `density_pre`, `density_post`, and `density_D`.
  The source `analytics.intervention_passes` table repeats intervention metadata
  on each pass row by design; it is not the central modeling dataset.

- Run the complete current build pipeline from the repository root with:
  `python PIPELINE.py`. This rebuilds `staging.events`,
  `analytics.intervention_passes` and the combined modeling CSV in dependency
  order without opening analysis plot windows. Run
  `python -m football_data.analysis.main_analysis` separately when you want
  the plots.

- By default, the modeling pipeline includes every eligible intervention
  action. Set `INTERVENTION_CONFIG["intervention_action"]` to a value such as
  `"Tackle"` in `main_analysis.py` when a single-action analysis is required.

### Next up
- Load one intervention from `analytics.intervention_passes` in Python and
  construct its pre/post edge lists.
- Define and test one network value `V(G)` before adding alternative measures.
- Keep ML, SHAP, Bayesian analysis, and composite disruption measures after
  the network construction and validation steps.
- AND FOLLOW THE PLAN ON PAPER!!
- good job so far:)

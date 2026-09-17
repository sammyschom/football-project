# football-project

My on-going football project, on the topic of football, data, analytics, visualisation...

How the pipeline works so far:

-----------------------------------------
THE FOLLOWING 2 TO BE RUN JUST DURING INITIAL SETUP, NOT IF DATA, OR DUCKDB ALREADY EXISTS
Downloads the raw statsbomb open data with:
python src/football_data/ingestion/statsbomb.py
Note: worst case you run and it says 'already exists' to everything

Build the database within duckdb
python sql-queries/data_loading.py
Note: running this would lose custom changes made to 'competitions, matches, events and lineups' 
but shouldn't be an issue as plan is to make more 'custom' table 
but can be useful for if the statsbomb open data were to get updated ever...

-----------------------------------------

Explore the database with SQL (embedded in python):
sql-queries/sql_queries.py


To come: 
export query results into pandas 
Build ML features and models in python (not SQL)
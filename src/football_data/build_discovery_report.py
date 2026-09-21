
from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd

# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # back to the project root

DATABASE_PATH = (
    PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
)

OUTPUT_DIR = PROJECT_ROOT / "output" / "discovery"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_PATH = OUTPUT_DIR / "statsbomb_discovery_report.html"


# --------------------------------------------------
# MY 'JUPYTER NOTEBOOK' STYLE SQL QUERIES
# Add new queries to this list as you go.
# --------------------------------------------------

queries = [

    {
        "title": "01 — Database tables",
        "purpose": (
            "List the tables currently available "
            "in the DuckDB database."
        ),
        "sql": """
            SELECT
                table_schema,
                table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN (
                'information_schema',
                'pg_catalog'
            )
            ORDER BY
                table_schema,
                table_name
        """
    },


    {
        "title": "02 — Competition and season inventory",
        "purpose": (
            "Identify the competitions and seasons "
            "available in the database."
        ),
        "sql": """
            SELECT
                competition_id,
                competition_name,
                season_id,
                season_name
            FROM competitions
            ORDER BY
                competition_name,
                season_name
        """
    },

    

    {
        "title": "03 — Database column inventory",
        "purpose": (
            "Explore the columns and data types "
            "available across the database."
        ),
        "sql": """
            SELECT
                table_name,
                ordinal_position,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema NOT IN (
                'information_schema',
                'pg_catalog'
            )
            ORDER BY
                table_name,
                ordinal_position
        """
    },
]


# --------------------------------------------------
# BUILD REPORT
# --------------------------------------------------

con = duckdb.connect(str(DATABASE_PATH), read_only=True)

report_sections = []

try:
    for query in queries:

        print(f"Running: {query['title']}")

        try:
            # Execute query and retrieve ALL result rows
            df = con.execute(query["sql"]).fetchdf()

            # Save the individual result as CSV
            csv_name = (
                query["title"]
                .split("—")[0]
                .strip()
                .replace(" ", "_")
                + ".csv"
            )

            df.to_csv(
                OUTPUT_DIR / csv_name,
                index=False
            )

            # Create a formatted HTML table
            table_html = df.to_html(
                index=False,
                border=0,
                classes="data-table",
                escape=True
            )

            section_html = f"""
            <section class="report-section">

                <h2>{query['title']}</h2>

                <p class="purpose">
                    {query['purpose']}
                </p>

                <div class="metadata">
                    {len(df):,} rows ·
                    {len(df.columns):,} columns
                </div>

                <details>
                    <summary>View SQL query</summary>
                    <pre><code>{query['sql']}</code></pre>
                </details>

                <div class="table-container">
                    {table_html}
                </div>

            </section>
            """

            report_sections.append(section_html)

        except Exception as e:
            report_sections.append(
                f"""
                <section class="report-section">
                    <h2>{query['title']}</h2>
                    <p>Query failed: {str(e)}</p>
                </section>
                """
            )

finally:
    con.close()


# --------------------------------------------------
# HTML REPORT TEMPLATE
# --------------------------------------------------

html = f"""
<!DOCTYPE html>
<html lang="en">

<head>
<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>StatsBomb Data Discovery</title>

<style>

body {{
    font-family: Arial, sans-serif;
    background: #f4f6f9;
    color: #172033;
    margin: 0;
    padding: 0;
}}

header {{
    background: #152238;
    color: white;
    padding: 40px 6%;
}}

header h1 {{
    margin: 0 0 12px;
    font-size: 30px;
}}

header p {{
    color: #cbd5e1;
    margin: 0;
}}

main {{
    max-width: 1400px;
    margin: auto;
    padding: 30px 4%;
}}

.report-section {{
    background: white;
    padding: 28px;
    margin-bottom: 28px;
    border-radius: 12px;
    box-shadow: 0 2px 10px #0000000c;
}}

h2 {{
    margin-top: 0;
    color: #152238;
}}

.purpose {{
    color: #526176;
}}

.metadata {{
    font-size: 13px;
    color: #64748b;
    margin: 16px 0;
}}

.table-container {{
    overflow-x: auto;
    max-height: 650px;
    overflow-y: auto;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}}

.data-table {{
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
    white-space: nowrap;
}}

.data-table th {{
    background: #eaf0f7;
    color: #152238;
    text-align: left;
    position: sticky;
    top: 0;
    z-index: 1;
}}

.data-table th,
.data-table td {{
    padding: 10px 14px;
    border-bottom: 1px solid #e8edf3;
}}

.data-table tr:nth-child(even) {{
    background: #f8fafc;
}}

details {{
    margin: 16px 0;
}}

pre {{
    background: #152238;
    color: #e2e8f0;
    padding: 16px;
    overflow-x: auto;
    border-radius: 8px;
}}

footer {{
    color: #64748b;
    text-align: center;
    padding: 30px;
}}

</style>
</head>

<body>

<header>
    <h1>StatsBomb Open Data</h1>
    <p>Data Discovery & Coverage Report</p>
    <p>Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}</p>
</header>

<main>

    <section class="report-section">
        <h2>Report overview</h2>
        <p>
            This report consolidates the results of
            exploratory SQL queries against the
            StatsBomb DuckDB database.
        </p>
        <p>
            Queries included:
            {len(queries)}
        </p>
    </section>

    {''.join(report_sections)}

</main>

<footer>
    StatsBomb Open Data · SQL Discovery
</footer>

</body>
</html>
"""


# --------------------------------------------------
# SAVE REPORT
# --------------------------------------------------

REPORT_PATH.write_text(
    html,
    encoding="utf-8"
)

print()
print("Report generated successfully:")
print(REPORT_PATH)
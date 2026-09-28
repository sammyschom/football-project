from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"


CREATE_STAGING_EVENTS = """
CREATE OR REPLACE TABLE staging.events AS
WITH source_events AS (
    SELECT
        TRY_CAST(
            regexp_extract(filename, '([0-9]+)[.]json$', 1)
            AS BIGINT
        ) AS match_id,
        *
    FROM main.events
)
SELECT
    match_id,
    id AS event_id,
    index AS event_index,
    period,
    timestamp,
    minute,
    second,
    type.id AS event_type_id,
    type.name AS event_type,
    possession,
    possession_team.id AS possession_team_id,
    possession_team.name AS possession_team,
    play_pattern.name AS play_pattern,
    team.id AS team_id,
    team.name AS team,
    player.id AS player_id,
    player.name AS player,
    position.id AS position_id,
    position.name AS position,
    location[1] AS location_x,
    location[2] AS location_y,
    under_pressure,
    counterpress,
    pass.recipient.id AS pass_recipient_id,
    pass.recipient.name AS pass_recipient,
    pass.length AS pass_length,
    pass.angle AS pass_angle,
    pass.height.name AS pass_height,
    pass.end_location[1] AS pass_end_x,
    pass.end_location[2] AS pass_end_y,
    pass.outcome.name AS pass_outcome,
    carry.end_location[1] AS carry_end_x,
    carry.end_location[2] AS carry_end_y,
    filename AS source_filename
FROM source_events
"""


def build_staging_events(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS staging")
    connection.execute(CREATE_STAGING_EVENTS)


def validate_staging_events(connection: duckdb.DuckDBPyConnection) -> None:
    duplicate_keys = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT match_id, event_index
            FROM staging.events
            GROUP BY match_id, event_index
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    missing_match_ids = connection.execute(
        """
        SELECT COUNT(*)
        FROM staging.events
        WHERE match_id IS NULL OR event_id IS NULL OR event_index IS NULL
        """
    ).fetchone()[0]

    if duplicate_keys or missing_match_ids:
        raise ValueError(
            "staging.events validation failed: "
            f"duplicate keys={duplicate_keys}, "
            f"missing identifiers={missing_match_ids}"
        )


def main() -> None:
    with duckdb.connect(str(DATABASE_PATH)) as connection:
        build_staging_events(connection)
        validate_staging_events(connection)

        summary = connection.execute(
            """
            SELECT
                COUNT(*) AS event_count,
                COUNT(DISTINCT match_id) AS match_count,
                COUNT(DISTINCT event_type) AS event_type_count
            FROM staging.events
            """
        ).fetchone()

    print(
        "Built staging.events: "
        f"{summary[0]:,} events, "
        f"{summary[1]:,} matches, "
        f"{summary[2]:,} event types"
    )


if __name__ == "__main__":
    main()
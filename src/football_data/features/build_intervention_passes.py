from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"

WINDOW_SIZE = 5


CREATE_INTERVENTION_PASSES = """
CREATE OR REPLACE TABLE analytics.intervention_passes AS
WITH pressure_events AS (
    SELECT
        match_id,
        event_id AS intervention_id,
        event_index AS intervention_event_index,
        period AS intervention_period,
        timestamp AS intervention_timestamp,
        minute AS intervention_minute,
        second AS intervention_second,
        team_id AS defending_team_id,
        team AS defending_team,
        player_id AS defender_id,
        player AS defender,
        position_id AS defender_position_id,
        position AS defender_position,
        possession AS pressured_possession,
        possession_team_id AS opponent_team_id,
        possession_team AS opponent_team,
        location_x AS intervention_location_x,
        location_y AS intervention_location_y,
        event_type AS intervention_action,
        match_context.match_date,
        match_context.kick_off,
        match_context.competition.competition_id AS competition_id,
        match_context.competition.competition_name AS competition,
        match_context.season.season_id AS season_id,
        match_context.season.season_name AS season,
        match_context.home_team.home_team_id AS home_team_id,
        match_context.home_team.home_team_name AS home_team,
        match_context.away_team.away_team_id AS away_team_id,
        match_context.away_team.away_team_name AS away_team,
        match_context.home_score,
        match_context.away_score,
        match_context.match_status
    FROM staging.events
    JOIN matches AS match_context USING (match_id)
    WHERE event_type = 'Pressure'
      AND team_id IS NOT NULL
            AND player_id IS NOT NULL
      AND possession_team_id IS NOT NULL
      AND team_id <> possession_team_id
), opponent_passes AS (
    SELECT
        match_id,
        event_id AS pass_event_id,
        event_index AS pass_event_index,
        period AS pass_period,
        timestamp AS pass_timestamp,
        possession,
        team_id,
        team,
        player_id AS passer_id,
        player AS passer,
        pass_recipient_id AS receiver_id,
        pass_recipient AS receiver,
        location_x AS pass_start_x,
        location_y AS pass_start_y,
        pass_end_x,
        pass_end_y,
        pass_length,
        pass_angle,
        pass_height,
        pass_outcome,
        under_pressure
    FROM staging.events
    WHERE event_type = 'Pass'
      AND pass_recipient_id IS NOT NULL
), candidate_passes AS (
    SELECT
        pressure.*,
        passes.* EXCLUDE (match_id, possession, team_id, team),
        CASE
            WHEN passes.pass_event_index < pressure.intervention_event_index
                THEN 'pre'
            ELSE 'post'
        END AS phase,
        ROW_NUMBER() OVER (
            PARTITION BY pressure.intervention_id,
                CASE
                    WHEN passes.pass_event_index < pressure.intervention_event_index
                        THEN 'pre'
                    ELSE 'post'
                END
            ORDER BY
                CASE
                    WHEN passes.pass_event_index < pressure.intervention_event_index
                        THEN passes.pass_event_index
                END DESC,
                CASE
                    WHEN passes.pass_event_index > pressure.intervention_event_index
                        THEN passes.pass_event_index
                END ASC
        ) AS window_pass_number
    FROM pressure_events AS pressure
    JOIN opponent_passes AS passes
      ON passes.match_id = pressure.match_id
     AND passes.possession = pressure.pressured_possession
     AND passes.team_id = pressure.opponent_team_id
     AND passes.pass_event_index <> pressure.intervention_event_index
), selected_passes AS (
    SELECT *
    FROM candidate_passes
    WHERE window_pass_number <= {window_size}
), complete_interventions AS (
    SELECT intervention_id
    FROM selected_passes
    GROUP BY intervention_id
    HAVING COUNT(*) FILTER (WHERE phase = 'pre') = {window_size}
       AND COUNT(*) FILTER (WHERE phase = 'post') = {window_size}
)
SELECT
    selected_passes.*,
    CASE
        WHEN phase = 'pre' THEN -window_pass_number
        ELSE window_pass_number
    END AS relative_pass_number
FROM selected_passes
JOIN complete_interventions USING (intervention_id)
ORDER BY match_id, intervention_event_index, phase, window_pass_number
""".format(window_size=WINDOW_SIZE)


def build_intervention_passes(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    connection.execute(CREATE_INTERVENTION_PASSES)


def validate_intervention_passes(connection: duckdb.DuckDBPyConnection) -> None:
    invalid_windows = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT intervention_id
            FROM analytics.intervention_passes
            GROUP BY intervention_id
            HAVING COUNT(*) <> 10
                OR COUNT(*) FILTER (WHERE phase = 'pre') <> 5
                OR COUNT(*) FILTER (WHERE phase = 'post') <> 5
                OR COUNT(DISTINCT relative_pass_number) <> 10
                OR MIN(relative_pass_number) <> -5
                OR MAX(relative_pass_number) <> 5
                OR COUNT(*) FILTER (WHERE relative_pass_number = 0) <> 0
        )
        """
    ).fetchone()[0]

    duplicate_passes = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT intervention_id, pass_event_id
            FROM analytics.intervention_passes
            GROUP BY intervention_id, pass_event_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    if invalid_windows or duplicate_passes:
        raise ValueError(
            "analytics.intervention_passes validation failed: "
            f"invalid windows={invalid_windows}, "
            f"duplicate intervention/pass pairs={duplicate_passes}"
        )


def main() -> None:
    with duckdb.connect(str(DATABASE_PATH)) as connection:
        build_intervention_passes(connection)
        validate_intervention_passes(connection)

        summary = connection.execute(
            """
            SELECT
                COUNT(*) AS pass_rows,
                COUNT(DISTINCT intervention_id) AS intervention_count,
                COUNT(DISTINCT match_id) AS match_count
            FROM analytics.intervention_passes
            """
        ).fetchone()

    print(
        "Built analytics.intervention_passes: "
        f"{summary[1]:,} interventions, "
        f"{summary[0]:,} pass rows, "
        f"{summary[2]:,} matches"
    )


if __name__ == "__main__":
    main()
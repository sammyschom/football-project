# imports as they come 
import duckdb
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt



PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "output" / "analysis"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

"""
Ball Recovery
Clearance
Dispossessed
Foul Committed
Interception
Pressure
"""
          
# Configure the intervention type analysed by this script.
INTERVENTION_CONFIG = {
    "intervention_action": "Ball Recovery",
}

# keys for the graph and edges, which are used in building the edges and nodes tables
GRAPH_KEYS = [
    "match_id",
    "intervention_id",
    "phase",
]

EDGE_KEYS = [
    *GRAPH_KEYS,
    "passer_id",
    "receiver_id",
]

# note the passing number window is a param adjusted in building
# the intervention passes table, and is not a param here.
# PRELIM: USING JUST PREMIER LEAGUE
def load_intervention_passes(intervention_action: str) -> pd.DataFrame:
    """Load intervention passes from the database."""
    intervention_action = (intervention_action or "").strip()
    if not intervention_action:
        raise ValueError("intervention_action cannot be empty.")

    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        df = connection.execute(
            """
            SELECT *
            FROM analytics.intervention_passes
            WHERE competition_id = 2 -- Premier League
              AND LOWER(intervention_action) = LOWER(?)
            """,
            [intervention_action],
        ).fetchdf()

    if df.empty:
        raise ValueError(
            f"No rows found for intervention_action={intervention_action!r}. "
            "Check the exact value in analytics.intervention_passes."
        )

    return df


def prepare_passes(df: pd.DataFrame) -> pd.DataFrame:
    """Keep passes only if there is a known passer and receiver,
       other wise its not a closed passing network!"""
    return df[
        df["passer_id"].notna()
        & df["receiver_id"].notna()
    ].copy()


def build_attempt_counts(passes: pd.DataFrame) -> pd.DataFrame:
    """Build a table of attempted passes for each intervention."""
    return (
        passes
        .groupby(GRAPH_KEYS, as_index=False)
        .agg(
            attempted_passes=("pass_event_id", "nunique"),
        )
    )


#===================================
# EDGES
#===================================

def build_frequency_edges(passes: pd.DataFrame) -> pd.DataFrame:
    """THE FIRST EDGE TYPE BUILDER: FREQUENCY EDGES, WHICH ARE JUST THE NUMBER OF PASSES BETWEEN TWO PLAYERS"""
    passes = passes.copy()
    passes["forward_progression"] = (
        passes["pass_end_x"] - passes["pass_start_x"]
    )
    edges = (
        passes
        .groupby(EDGE_KEYS, as_index=False) 
        .agg(
            pass_count=("pass_event_id", "nunique"),
            forward_progression=("forward_progression", "sum")
        )
    )
    edges["edge_weight"] = edges["pass_count"] #!!!
    return edges


EDGE_BUILDERS = {
    "frequency": build_frequency_edges, # for now just the frequency edges
}


def build_edges(
    passes: pd.DataFrame,
    representation: str,
) -> pd.DataFrame:
    try:
        builder = EDGE_BUILDERS[representation]
    except KeyError as error:
        available = ", ".join(EDGE_BUILDERS)
        raise ValueError(
            f"Unknown edge representation {representation!r}. "
            f"Choose from: {available}"
        ) from error

    return builder(passes)


#===================================
# NETWORK METRICS
#===================================


def evaluate_completion(
    edges: pd.DataFrame,
    attempted_passes: pd.DataFrame,
) -> pd.DataFrame:
    completed = (
        edges
        .groupby(GRAPH_KEYS, as_index=False)
        .agg(
            completed_passes=("edge_weight", "sum"),
        )
    )

    values = attempted_passes.merge(
        completed,
        on=GRAPH_KEYS,
        how="left",
    )

    values["completed_passes"] = (
        values["completed_passes"].fillna(0)
    )

    values["completion_rate"] = (
        values["completed_passes"]
        / values["attempted_passes"]
    )

    values["completion_value"] = values["completion_rate"]

    return values


def forward_progression(edges: pd.DataFrame, attempted_passes: pd.DataFrame,) -> pd.DataFrame:
    """Calculate how much forward progression is made by the passing network before and after the intervention.""" 
    # for before and after networks, work out the accumalated change in x (I believe). 
    # Higher forward progression is better, so a drop in forward progression is a disruption.
    progression = (
        edges
        .groupby(GRAPH_KEYS, as_index=False)
        .agg(
            forward_progression=("forward_progression", "sum"),
        )
    )

    values = attempted_passes.merge(
        progression,
        on=GRAPH_KEYS,
        how="left",
    )

    values["forward_progression"] = (
        values["forward_progression"].fillna(0)
    )

    values["forward_progression_value"] = (
        values["forward_progression"]
        / values["attempted_passes"]
    )

    return values


NETWORK_METRICS = {
    "completion": evaluate_completion,
    "forward_progression": forward_progression,
}


def evaluate_network(
    edges: pd.DataFrame,
    attempted_passes: pd.DataFrame,
    metric: str,
) -> pd.DataFrame:
    try:
        evaluator = NETWORK_METRICS[metric]
    except KeyError as error:
        available = ", ".join(NETWORK_METRICS)
        raise ValueError(
            f"Unknown network metric {metric!r}. "
            f"Choose from: {available}"
        ) from error

    return evaluator(edges, attempted_passes)


def calculate_disruption(pre_value, post_value):
    return pre_value - post_value


def compare_values(
    values: pd.DataFrame,
    value_column: str,
) -> pd.DataFrame:
    comparison = (
        values
        .pivot(
            index=["match_id", "intervention_id"],
            columns="phase",
            values=value_column,
        )
        .reindex(columns=["pre", "post"])
        .reset_index()
        .rename(
            columns={
                "pre": "value_pre",
                "post": "value_post",
            }
        )
    )

    comparison["disruption"] = calculate_disruption(
        comparison["value_pre"],
        comparison["value_post"],
    )

    return comparison


def plot_network_disruption(
    comparison: pd.DataFrame,
    metric_label: str,
) -> None:

    data = comparison.dropna(
        subset=["value_pre", "value_post"]
    )

    number_of_interventions = data["intervention_id"].nunique()

    mean_pre = data["value_pre"].mean()
    mean_post = data["value_post"].mean()
    mean_disruption = data["disruption"].mean()

    fig, ax = plt.subplots(figsize=(8, 6))

    for row in data.itertuples():
        ax.plot(
            ["Before", "After"],
            [row.value_pre, row.value_post],
            color="grey",
            alpha=0.12,
            linewidth=0.8,
        )

    ax.plot(
        ["Before", "After"],
        [mean_pre, mean_post],
        color="#da0808",
        marker="o",
        markersize=9,
        linewidth=3,
        label="Average",
    )

    ax.set_ylabel(metric_label)

    ax.set_title(
    f"{metric_label} Before and After "
    f"{INTERVENTION_CONFIG['intervention_action']} Intervention\n"
    f"(n = {number_of_interventions:,} "
    f"{INTERVENTION_CONFIG['intervention_action'].lower()} interventions)"
    )
    

    ax.legend()

    ax.text(
        0.5,
        0.04,
        f"Average disruption: {mean_disruption:+.3f}",
        transform=ax.transAxes,
        ha="center",
    )

    plt.show()

METRIC_CONFIG = {
    "completion": {
        "value_column": "completion_value",
        "label": "Pass completion rate",
    },
    "forward_progression": {
        "value_column": "forward_progression_value",
        "label": "Forward progression per attempted pass",
    },
}

def main() -> None:


    intervention_passes = load_intervention_passes(
        INTERVENTION_CONFIG["intervention_action"]
    )

    valid_passes = prepare_passes(
        intervention_passes
    )

    attempted_passes = build_attempt_counts(
        valid_passes
    )

    completed_passes = valid_passes[
        valid_passes["pass_outcome"].isna()
    ].copy()

    edges = build_edges(
        completed_passes,
        "frequency",
    )

    for metric, config in METRIC_CONFIG.items():

        values = evaluate_network(
            edges,
            attempted_passes,
            metric,
        )

        comparison = compare_values(
            values,
            config["value_column"],
        )

        print(f"\n=== {metric.upper()} ===")

        print(
            comparison
            .head(20)
            .to_string(index=False)
        )

        print(
            f"Mean disruption: "
            f"{comparison['disruption'].mean():+.3f}"
        )

        print(
            "Positive disruption share: "
            f"{(comparison['disruption'] > 0).mean():.1%}"
        )

        plot_network_disruption(
            comparison,
            config["label"],
        )

if __name__ == "__main__":
    main()

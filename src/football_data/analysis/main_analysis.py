# imports as they come 
import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import matplotlib.pyplot as plt



PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "output" / "analysis"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# For reference, the eligible intervention actions (so far) are:
"""
Ball Recovery
Clearance
Dispossessed
Foul Committed
Interception
Pressure
Duel
Block
Tackle
(50_50)
"""
          
# Set to a specific action such as "Tackle" to filter the analysis.
# None analyses every eligible intervention action!
INTERVENTION_CONFIG = {
    "intervention_action": None,
}

# keys for the graph and edges, which are used in building the edges and nodes tables
# how i identify and group my data
GRAPH_KEYS = [
    "match_id",
    "intervention_id",
    "phase",
]

EDGE_KEYS = [
    *GRAPH_KEYS, #  * unpacks the list into the new list
    "passer_id",
    "receiver_id",
]

# (remember the passing number window is a param adjusted in building
# the intervention passes table, and is not a param here.)


# PRELIM: USING JUST PREMIER LEAGUE
def load_intervention_passes(intervention_action: Optional[str] = None,):
    """
    Load intervention passes from the database.
    Returns pandas dataframe with intervention passes, optionally filtered by intervention_action.
    """
    action_filter = (intervention_action or "").strip() # validate: leading or trailing whitespace, and convert None to empty string
    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        if action_filter:
            df = connection.execute(
                """
                SELECT *
                FROM analytics.intervention_passes
                WHERE LOWER(intervention_action) = LOWER(?)
                """,
                [action_filter],
            ).fetchdf()
        else:
            df = connection.execute(
                """
                SELECT *
                FROM analytics.intervention_passes
                """
            ).fetchdf()

    if df.empty:
        action_description = (
            f"intervention_action={action_filter!r}"
            if action_filter
            else "all intervention actions"
        )
        raise ValueError(
            f"No rows found for {action_description}. "
            "Check the exact value in analytics.intervention_passes."
        )

    return df


def prepare_passes(df: pd.DataFrame):
    """Keep passes only if there is a known passer and receiver,
       other wise its not a closed passing network!"""
    return df[
        df["passer_id"].notna()
        & df["receiver_id"].notna()
    ].copy()


def build_attempt_counts(passes: pd.DataFrame):
    """Build a table and count number  of attempted passes for each intervention."""
    return (
        passes
        .groupby(GRAPH_KEYS, as_index=False) # seperates the data into groups based on the specified keys, then prepares for aggregation
        .agg(                                # one row per intervention-phase network 
            attempted_passes=("pass_event_id", "nunique"),
        )
    )

#===================================
# EDGES
#===================================

# DOES THIS NEED TO BE DOING FORWARD_PROGRESSION HERE? METRIC? 
def build_frequency_edges(passes: pd.DataFrame):
    """THE FIRST EDGE TYPE BUILDER: FREQUENCY EDGES, WHICH ARE JUST THE NUMBER OF PASSES BETWEEN TWO PLAYERS -- directed!"""
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


def build_edges(passes: pd.DataFrame, representation: str,):
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


def evaluate_completion(edges: pd.DataFrame, attempted_passes: pd.DataFrame,):
    """Calculate pass completion rate for each intervention-phase network."""
    
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


def density(edges: pd.DataFrame, attempted_passes: pd.DataFrame,) -> pd.DataFrame:
    """Calculate directed passing-network density.

    Nodes are the union of passers and receivers. Each distinct passer to
    receiver pair is one directed edge, so the maximum is n * (n - 1).
    """
    node_frames = [
        edges[GRAPH_KEYS + ["passer_id"]].rename(
            columns={"passer_id": "player_id"}
        ),
        edges[GRAPH_KEYS + ["receiver_id"]].rename(
            columns={"receiver_id": "player_id"}
        ),
    ]
    nodes = pd.concat(node_frames, ignore_index=True).drop_duplicates()
    player_counts = (
        nodes
        .groupby(GRAPH_KEYS, as_index=False)
        .agg(unique_players=("player_id", "nunique"))
    )
    edges_count = (
        edges
        .groupby(GRAPH_KEYS, as_index=False)
        .agg(actual_edges=("edge_weight", "size"))
    )
    values = attempted_passes[GRAPH_KEYS].drop_duplicates().merge(
        player_counts,
        on=GRAPH_KEYS,
        how="left",
    ).merge(
        edges_count,
        on=GRAPH_KEYS,
        how="left",
    )
    values[["unique_players", "actual_edges"]] = values[
        ["unique_players", "actual_edges"]
    ].fillna(0)
    values["possible_edges"] = (
        values["unique_players"] * (values["unique_players"] - 1)
    )
    values["density"] = 0.0
    non_empty_network = values["possible_edges"] > 0
    values.loc[non_empty_network, "density"] = (
        values.loc[non_empty_network, "actual_edges"]
        / values.loc[non_empty_network, "possible_edges"]
    )
    return values


NETWORK_METRICS = {
    "completion": evaluate_completion,
    "forward_progression": forward_progression,
    "density": density,
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
        label=None,
    )

    ax.set_ylabel(metric_label)

    configured_action = INTERVENTION_CONFIG["intervention_action"]
    action_label = configured_action or "All"
    ax.set_title(
        f"{metric_label} Before and After "
        f"{action_label} Intervention\n"
        f"(n = {number_of_interventions:,} "
        f"{action_label.lower()} interventions)"
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
    "density": {
        "value_column": "density",
        "label": "Passing network density",
    },
}


MODEL_COLUMNS = [
    "match_id",
    "intervention_id",
    "defender_id",
    "defender",
    "intervention_action",
    "G_pre",
    "G_post",
    "D",
]


def combine_modeling_datasets(
    datasets: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Combine metric-specific intervention rows into one wide dataset."""
    if not datasets:
        raise ValueError("At least one metric dataset is required.")

    key_columns = ["match_id", "intervention_id"]
    first_dataset = next(iter(datasets.values()))
    combined = first_dataset[
        [
            *key_columns,
            "defender_id",
            "defender",
            "intervention_action",
        ]
    ].copy()

    for metric, dataset in datasets.items():
        if not dataset.set_index(key_columns).index.is_unique:
            raise ValueError(
                f"{metric} modeling dataset has duplicate interventions."
            )

        metric_values = dataset[
            [*key_columns, "G_pre", "G_post", "D"]
        ].rename(
            columns={
                "G_pre": f"{metric}_pre",
                "G_post": f"{metric}_post",
                "D": f"{metric}_D",
            }
        )
        combined = combined.merge(
            metric_values,
            on=key_columns,
            how="outer",
            validate="one_to_one",
        )

    if combined.isna().any().any():
        raise ValueError(
            "Combined modeling dataset contains missing values after "
            "joining metric datasets."
        )

    return combined.sort_values(key_columns).reset_index(drop=True)


def build_modeling_dataset(
    passes: pd.DataFrame,
    completed_passes: pd.DataFrame,
    attempted_passes: pd.DataFrame,
    metric: str,
) -> pd.DataFrame:
    """Build one modeling row per intervention.

    ``G_pre`` and ``G_post`` are scalar network values. ``D`` is the
    disruption for the selected network metric: V(G_pre) - V(G_post).
    """
    try:
        config = METRIC_CONFIG[metric]
    except KeyError as error:
        available = ", ".join(METRIC_CONFIG)
        raise ValueError(
            f"Unknown modeling metric {metric!r}. Choose from: {available}"
        ) from error

    intervention_keys = ["match_id", "intervention_id"]
    metadata_columns = [
        *intervention_keys,
        "defender_id",
        "defender",
        "intervention_action",
    ]
    metadata = passes[metadata_columns].drop_duplicates()
    inconsistent_metadata = (
        metadata
        .groupby(intervention_keys, as_index=False)
        .size()
        .loc[lambda rows: rows["size"] > 1]
    )
    if not inconsistent_metadata.empty:
        raise ValueError(
            "An intervention has inconsistent metadata across its pass rows: "
            f"{inconsistent_metadata[intervention_keys].to_dict(orient='records')}"
        )

    edges = build_edges(completed_passes, "frequency")
    values = evaluate_network(
        edges,
        attempted_passes,
        metric,
    )
    comparison = compare_values(values, config["value_column"])

    modeling_dataset = (
        metadata
        .merge(
            comparison[
                [
                    "match_id",
                    "intervention_id",
                    "value_pre",
                    "value_post",
                    "disruption",
                ]
            ],
            on=["match_id", "intervention_id"],
            how="inner",
        )
        .rename(
            columns={
                "value_pre": "G_pre",
                "value_post": "G_post",
                "disruption": "D",
            }
        )
    )

    missing_columns = [
        column for column in MODEL_COLUMNS if column not in modeling_dataset
    ]
    if missing_columns:
        raise ValueError(
            f"Modeling dataset is missing required columns: {missing_columns}"
        )

    return modeling_dataset[MODEL_COLUMNS].sort_values(
        ["match_id", "intervention_id"]
    ).reset_index(drop=True)


def main(show_plots: bool = True) -> None:


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

    metric_datasets = {}
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

        modeling_dataset = build_modeling_dataset(
            valid_passes,
            completed_passes,
            attempted_passes,
            metric,
        )
        metric_datasets[metric] = modeling_dataset

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

        if show_plots:
            plot_network_disruption(
                comparison,
                config["label"],
            )

    combined_dataset = combine_modeling_datasets(metric_datasets)
    combined_dataset.to_csv(
        OUTPUT_DIR / "modeling_dataset.csv",
        index=False,
    )
    print(
        f"\n=== COMBINED MODELING DATASET ===\n"
        f"Rows: {len(combined_dataset):,}\n"
        f"Columns: {len(combined_dataset.columns):,}"
    )


if __name__ == "__main__":
    main()

# imports as they come 
import duckdb
import pandas as pd
from pathlib import Path

# first thing to do is to take analytics.intervention_passes from the duckdb 

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "statsbomb.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "output" / "analysis"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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
def load_intervention_passes():
    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        return connection.execute(
        "SELECT * FROM analytics.intervention_passes WHERE competition_id = 2 -- Premier League" 
         ).fetchdf()

def prepare_passes(df: pd.DataFrame) -> pd.DataFrame:
    """Keep valid directed passes and derive reusable pass attributes."""
    passes = df.copy()

    # filter out passes that don't have a passer or receiver
    passes = passes[
        passes["passer_id"].notna()
        & passes["receiver_id"].notna()
    ].copy()

    # Use this filter if the network should contain completed passes only: !!!
    passes = passes[passes["pass_outcome"].isna()].copy()

    return passes

# NOW ON TO CREATING THE EDGES:
# for now just focussing on simple edges: number of passes between two players
def build_frequency_edges(passes: pd.DataFrame) -> pd.DataFrame:
    edges = (
        passes
        .groupby(EDGE_KEYS, as_index=False)
        .agg(
            pass_count=("pass_event_id", "nunique"),
        )
    )
    edges["edge_weight"] = edges["pass_count"]

    return edges


# to be expanded as i add in more edge types, but for now just the frequency edges...
EDGE_BUILDERS = {
    "frequency": build_frequency_edges,
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


# at this point, and for now, have an edge table, with who passes to who and how many times.
def main() -> None:
    intervention_passes = load_intervention_passes()
    passes = prepare_passes(intervention_passes)
    frequency_edges = build_edges(passes, "frequency")
    #print(frequency_edges.head())
    print(
    frequency_edges
    .groupby(["match_id", "intervention_id", "phase"])["pass_count"]
    .agg(["count", "sum", "max"])
    .head(20)
)
    
if __name__ == "__main__":
    main()

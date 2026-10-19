"""Run the football data build pipeline from the repository root."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from football_data.analysis.main_analysis import main as build_modeling_datasets
from football_data.features.build_intervention_passes import (
    main as build_intervention_passes,
)
from football_data.features.build_staging_events import (
    main as build_staging_events,
)


def main() -> None:
    """Build all processed tables and modeling datasets in dependency order."""
    print("=== Building staging events ===")
    build_staging_events()

    print("\n=== Building intervention pass windows ===")
    build_intervention_passes()

    print("\n=== Building modeling datasets ===")
    build_modeling_datasets(show_plots=False)

    expected_outputs = [
        PROJECT_ROOT / "output" / "analysis" / "modeling_dataset.csv"
    ]
    missing_outputs = [
        path for path in expected_outputs if not path.is_file()
    ]
    if missing_outputs:
        missing = ", ".join(str(path) for path in missing_outputs)
        raise RuntimeError(f"Pipeline did not create expected outputs: {missing}")

    print("\nCreated modeling datasets:")
    for output_path in expected_outputs:
        print(f"- {output_path}")

    print("\n=== Pipeline completed successfully ===")


if __name__ == "__main__":
    main()
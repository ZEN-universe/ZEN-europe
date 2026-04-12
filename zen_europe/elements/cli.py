import argparse
from pathlib import Path

from zen_europe.elements.runner import run


def zen_europe_cli() -> None:
    parser = argparse.ArgumentParser(description="Run the ZEN Europe model")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the model configuration file.",
    )
    args = parser.parse_args()
    run(args.config)

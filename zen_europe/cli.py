import argparse
from pathlib import Path

from zen_europe.model_creator import create_model


def zen_europe_cli() -> None:
    parser = argparse.ArgumentParser(description="Run the ZEN Europe model")
    parser.add_argument(
        "--config",
        type=Path,
        required=False,
        default=None,
        help="Path to the model configuration file.",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=False,
        default="zen-europe",
        help="Name of the model that will be used when saving.",
    )
    parser.add_argument(
        "--output_folder",
        type=Path,
        required=False,
        default=".",
        help="Output directory to which the model will be saved.",
    )
    args = parser.parse_args()

    create_model(config=args.config, name=args.name, output_folder=args.output_folder)

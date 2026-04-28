import argparse
from pathlib import Path

from zen_europe.model_creator import create_model

COLOR_SUCCESS = "\033[92m"
COLOR_RESET = "\033[0m"


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
        "--output-folder",
        type=Path,
        required=False,
        default=".",
        help="Output directory to which the model will be saved.",
    )
    args = parser.parse_args()

    print(f"Generating model '{args.name}' ...")
    create_model(config=args.config, name=args.name, output_folder=args.output_folder)
    path = (args.output_folder / args.name).resolve()
    print(
        COLOR_SUCCESS
        + f"Successfully generated model '{args.name}' and saved to {path}/"
        + COLOR_RESET
    )

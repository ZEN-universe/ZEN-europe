import argparse
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from zen_creator.utils.config import Config
from zen_creator.utils.settings import ModelSet, Settings

from zen_europe.model_creator import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_OUTPUT_PATH,
    create_model,
    default_models_path,
)
from zen_europe.settings.cache import clear_caches

COLOR_SUCCESS = "\033[92m"
COLOR_WARNING = "\033[38;5;208m"  # orange
COLOR_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    """Formatter that colors WARNING-level records orange."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        if record.levelno == logging.WARNING:
            return f"{COLOR_WARNING}{message}{COLOR_RESET}"
        return message


_handler = logging.StreamHandler()
_handler.setFormatter(_ColorFormatter("%(levelname)s - %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger(__name__)

DEFAULT_JOBS = min(4, os.cpu_count() or 1)


def zen_europe_cli() -> None:
    parser = argparse.ArgumentParser(description="Run the ZEN-europe model")
    parser.add_argument(
        "--config_path",
        type=Path,
        required=False,
        default=None,
        help=(
            "Path to the model configuration file "
            "(default: data/zen_europe_config.yaml)."
        ),
    )
    parser.add_argument(
        "--models_path",
        type=Path,
        required=False,
        default=None,
        help=(
            "Path to the models file declaring the model variants "
            "(default: models.yaml next to the configuration file)."
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        required=False,
        default=None,
        help="Name of the variant in the models file to generate.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate every variant declared in the models file.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        required=False,
        default=None,
        help=(
            "Number of variants to generate at once with --all "
            f"(default: {DEFAULT_JOBS})."
        ),
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help=(
            "Generate the variants of --all one after another in this "
            "process, which makes debugging easier."
        ),
    )
    parser.add_argument(
        "--name",
        type=str,
        required=False,
        default="zen-europe",
        help=(
            "Name of the model that will be used when saving. Ignored with "
            "--model or --all, which name each dataset after the models file."
        ),
    )
    parser.add_argument(
        "--output_path",
        type=Path,
        required=False,
        default=None,
        help=(
            "Directory the datasets are written to, together with the "
            "config.yaml that ZEN-garden is run with. Overrides output.path "
            f"from the settings (default: {DEFAULT_OUTPUT_PATH})."
        ),
    )
    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help=(
            "Delete all registered downloaded source snapshots and derived "
            "dataset caches before generating models."
        ),
    )
    args = parser.parse_args()

    if args.all and args.model:
        parser.error("--all and --model cannot be combined.")
    if args.sequential and not args.all:
        parser.error("--sequential only applies together with --all.")
    if args.jobs is not None and not args.all:
        parser.error("--jobs only applies together with --all.")

    if args.no_incremental:
        _clear_caches(args.config_path or DEFAULT_CONFIG_PATH)

    if args.all:
        _generate_all(args)
    else:
        _generate_one(args)


def _generate_one(args: argparse.Namespace) -> None:
    """Generate a single dataset, with or without a variant."""
    name = args.model or args.name

    logger.info(f"Generating model '{name}' ...")
    model = create_model(
        config=args.config_path,
        models=args.models_path,
        model_name=args.model,
        name=args.name,
        output_folder=args.output_path,
    )
    _log_success(name, model.output_folder)


def _generate_all(args: argparse.Namespace) -> None:
    """Generate every variant declared in the models file."""
    config = args.config_path or DEFAULT_CONFIG_PATH
    models_path = args.models_path or default_models_path(config)

    model_set = ModelSet.load_from_yaml(models_path)

    # resolve every variant up front, so that a mistake in the models file
    # is reported before any data is read
    resolved = {
        name: Settings.load_from_yaml(config, patch=model_set.settings_patch(name))
        for name in model_set.names
    }

    logger.info(
        f"Generating {len(resolved)} models from {models_path}: "
        f"{', '.join(resolved)}"
    )

    if args.sequential:
        _generate_in_process(resolved, args, models_path)
        return

    jobs = args.jobs or DEFAULT_JOBS
    if args.no_incremental:
        logger.warning(
            "--no-incremental clears shared dataset caches, so models are "
            "generated one at a time while the caches are rebuilt."
        )
        jobs = 1
    elif _reloads_caches(resolved):
        logger.warning(
            "A model reloads a dataset cache from its source, so the models "
            "are generated one at a time to keep them from writing the same "
            "cache file at once."
        )
        jobs = 1

    _generate_in_subprocesses(resolved, args, models_path, jobs)


def _clear_caches(config_path: Path) -> None:
    """Delete registered cache files below the configured source path."""
    config = Config.load_from_yaml(config_path)
    if config.source_path is None:
        raise ValueError(
            "--no-incremental requires source_path to be set in the configuration."
        )
    removed = clear_caches(config.source_path)
    for path in removed:
        logger.info(f"Removed cache file {path}")
    logger.info(f"Removed {len(removed)} cache files before model generation.")


def _reloads_caches(resolved: dict[str, Settings]) -> bool:
    """Whether any model reloads a dataset cache from its source."""
    return any(
        any(settings.cache.model_dump().values()) for settings in resolved.values()
    )


def _generate_in_process(
    resolved: dict[str, Settings], args: argparse.Namespace, models_path: Path
) -> None:
    """Generate the models one after another in this process."""
    logger.warning(
        "Generating the models in this process, so they share the datasets "
        "that have already been loaded. Drop --sequential to generate each "
        "model in its own process."
    )

    for name in resolved:
        logger.info(f"Generating model '{name}' ...")
        model = create_model(
            config=args.config_path,
            models=models_path,
            model_name=name,
            output_folder=args.output_path,
        )
        _log_success(name, model.output_folder)


def _generate_in_subprocesses(
    resolved: dict[str, Settings],
    args: argparse.Namespace,
    models_path: Path,
    jobs: int,
) -> None:
    """Generate each model in its own process, up to `jobs` at a time.

    The output of a model is captured and only shown when it fails, so that
    models running at the same time do not interleave their logs.
    """
    failed: list[str] = []

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {}
        for name in resolved:
            logger.info(f"Generating model '{name}' ...")
            command = _command_for(name, args, models_path)
            futures[pool.submit(_run, command)] = name

        for future in as_completed(futures):
            name = futures[future]
            result = future.result()
            if result.returncode == 0:
                output_folder = args.output_path or resolved[name].output.path
                _log_success(name, output_folder)
                continue

            failed.append(name)
            logger.error(
                f"Generating model '{name}' failed with exit code "
                f"{result.returncode}."
            )
            if result.stderr:
                logger.error(result.stderr.strip())

    if failed:
        raise SystemExit(f"Failed to generate: {', '.join(sorted(failed))}")


def _run(command: list[str]) -> "subprocess.CompletedProcess[str]":
    """Run a command, capturing its output."""
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _command_for(name: str, args: argparse.Namespace, models_path: Path) -> list[str]:
    """The command that generates a single model in its own process.

    The interpreter that runs this process is reused, so that a subprocess
    does not depend on which python is first on the PATH.
    """
    command = [
        sys.executable,
        "-m",
        "zen_europe",
        "--model",
        name,
        "--models_path",
        str(models_path),
    ]
    if args.output_path is not None:
        command += ["--output_path", str(args.output_path)]
    if args.config_path is not None:
        command += ["--config_path", str(args.config_path)]

    return command


def _log_success(name: str, output_folder: Path) -> None:
    """Report where a generated model was saved."""
    path = (Path(output_folder) / name).resolve()
    logger.info(
        COLOR_SUCCESS
        + f"Successfully generated model '{name}' and saved to {path}/"
        + COLOR_RESET
    )

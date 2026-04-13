"""End-to-end tests for runner and CLI entry point."""

from __future__ import annotations

from pathlib import Path

from zen_europe.model_creator import create_model
from zen_europe.cli import zen_europe_cli
import sys



def test_create_model() -> None:
    """Test that runner.run() executes without errors."""
    test_path = Path(__file__).resolve().parent
    create_model(name="test_model", output_folder= test_path / "outputs")


def test_zen_europe_cli_entry_point(monkeypatch) -> None:
    # Simulate: program_name --config config.toml --name test --output_dir out
    test_path = Path(__file__).resolve().parent
    output_path = str(test_path / "outputs")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "zen-europe",
            "--name",
            "test_model_cli",
            "--output_folder",
            output_path,
        ],
    )

    zen_europe_cli()
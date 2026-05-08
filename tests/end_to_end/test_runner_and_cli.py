"""End-to-end tests for runner and CLI entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from zen_europe.cli import zen_europe_cli
from zen_europe.model_creator import create_model


def test_create_model() -> None:
    """Test that runner.run() executes without errors."""
    test_path = Path(__file__).resolve().parent
    create_model(name="test_model", output_folder=test_path / "outputs")


def test_model_structure() -> None:
    """Test that the created model has the expected structure."""
    test_path = Path(__file__).resolve().parent
    model = create_model(
        name="test_model_structure", output_folder=test_path / "outputs", write=False
    )

    cn = "zen_europe.elements.energy_systems.zen_europe_nuts0.EnergySystemNuts0"
    assert str(type(model.energy_system)) == f"<class '{cn}'>"
    cn = "zen_europe.elements.conversion_technologies.photovoltaics.Photovoltaics"
    assert str(type(model.elements["photovoltaics"])) == f"<class '{cn}'>"
    cn = "zen_europe.elements.carriers.electricity.Electricity"
    assert str(type(model.elements["electricity"])) == f"<class '{cn}'>"
    cn = "zen_europe.elements.transport_technologies.power_line.PowerLine"
    assert str(type(model.elements["power_line"])) == f"<class '{cn}'>"
    cn = "zen_europe.elements.storage_technologies.pumped_hydro.PumpedHydro"
    assert str(type(model.elements["pumped_hydro"])) == f"<class '{cn}'>"


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
            "--output-folder",
            output_path,
        ],
    )

    zen_europe_cli()

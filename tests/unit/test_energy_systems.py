"""Unit tests for energy_systems module exports and singleton construction."""

from __future__ import annotations

from typing import Any, cast

from zen_creator import EnergySystem
from zen_creator.model import Model

import zen_europe.elements.energy_systems as energy_systems_module


def _energy_system_classes(model: Model) -> list[type[EnergySystem]]:
    """Return all energy system classes exported by the module."""
    classes: list[type[EnergySystem]] = []
    for name in energy_systems_module.__all__:
        energy_system_cls = getattr(energy_systems_module, name)
        if isinstance(energy_system_cls, type) and issubclass(
            energy_system_cls, EnergySystem
        ):
            classes.append(energy_system_cls)
    return classes


def _construct_energy_system(
    energy_system_cls: type[EnergySystem], model: Model
) -> EnergySystem:
    """Construct an energy system class with the expected constructor signature."""
    energy_system_factory = cast(type[Any], energy_system_cls)
    return cast(EnergySystem, energy_system_factory(model=model))


def test_all_importable_energy_systems_are_energy_system_classes(
    model: Model,
) -> None:
    """All importable module exports must be EnergySystem subclasses."""
    energy_system_classes = _energy_system_classes(model)
    assert energy_system_classes
    for energy_system_cls in energy_system_classes:
        assert issubclass(energy_system_cls, EnergySystem)


def test_all_importable_energy_systems_construct(
    model: Model,
) -> None:
    """All importable energy systems should construct successfully."""
    for energy_system_cls in _energy_system_classes(model):
        energy_system = _construct_energy_system(energy_system_cls, model)
        assert isinstance(energy_system, energy_system_cls)
        assert energy_system_cls.name

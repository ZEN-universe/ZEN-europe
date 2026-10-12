"""Unit tests for the concrete ZEN-europe Sector definitions."""

from __future__ import annotations

from zen_creator.elements import Element
from zen_creator.sectors import Sector

import zen_europe.elements.carriers  # noqa: F401
import zen_europe.elements.conversion_technologies  # noqa: F401
import zen_europe.elements.retrofitting_technologies  # noqa: F401
import zen_europe.elements.sectors as sectors_module
import zen_europe.elements.storage_technologies  # noqa: F401
import zen_europe.elements.transport_technologies  # noqa: F401


def _zen_europe_sectors() -> list[type[Sector]]:
    return [
        sector_cls
        for sector_cls in Sector._sector_registry.values()
        if sector_cls.__module__.startswith("zen_europe.elements.sectors")
    ]


def test_all_sectors_are_importable_from_package() -> None:
    """Every registered ZEN-europe sector is exported by the sectors package."""
    exported = {
        obj
        for name in dir(sectors_module)
        if isinstance(obj := getattr(sectors_module, name), type)
    }
    for sector_cls in _zen_europe_sectors():
        assert sector_cls in exported


def test_sector_elements_are_element_subclasses() -> None:
    """Every class a sector declares is a constructible Element subclass."""
    for sector_cls in _zen_europe_sectors():
        elements = sector_cls().elements
        assert elements
        for element_cls in elements:
            assert isinstance(element_cls, type)
            assert issubclass(element_cls, Element)


def test_gas_sector_has_no_required_sectors() -> None:
    """The gas sector is the root of the taxonomy."""
    from zen_europe.elements.sectors.gas import GasSector

    assert GasSector.required_sectors == []


def test_every_registered_technology_and_carrier_belongs_to_a_sector() -> None:
    """Every ZEN-europe carrier/technology is covered by at least one sector.

    Energy systems are excluded: they are selected individually via
    ``elements.insert.energy_system``, not via sectors.
    """
    from zen_creator.elements import EnergySystem

    owned_elements: set[type[Element]] = set()
    for sector_cls in _zen_europe_sectors():
        owned_elements.update(sector_cls().elements)

    registered = Element.get_registry()
    for name, element_cls in registered.items():
        if not element_cls.__module__.startswith("zen_europe.elements."):
            continue
        if issubclass(element_cls, EnergySystem):
            continue
        assert element_cls in owned_elements, (
            f"{name} ({element_cls.__module__}.{element_cls.__qualname__}) "
            "is not declared by any sector."
        )

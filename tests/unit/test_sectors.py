"""Unit tests for the concrete ZEN-europe Sector definitions."""

from __future__ import annotations

import inspect
import re

from zen_creator import Model, model_structure
from zen_creator.elements import Element
from zen_creator.sectors import Sector
from zen_creator.utils.config import Config
from zen_creator.utils.settings import Settings

import zen_europe.elements.carriers  # noqa: F401
import zen_europe.elements.conversion_technologies  # noqa: F401
import zen_europe.elements.retrofitting_technologies  # noqa: F401
import zen_europe.elements.sectors as sectors_module
import zen_europe.elements.storage_technologies  # noqa: F401
import zen_europe.elements.transport_technologies  # noqa: F401
from zen_europe.model_creator import DATA_PATH, DEFAULT_CONFIG_PATH

CARRIER_ATTRIBUTES = [
    "reference_carrier",
    "input_carrier",
    "output_carrier",
    "retrofit_reference_carrier",
]
# an element that reads another element by name, e.g. model.elements["x"]
ELEMENT_REFERENCE = re.compile(
    r"model\.(?:elements|carriers|technologies)\[\s*[\"'](\w+)[\"']\s*\]"
)


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


def test_every_valid_sector_selection_is_complete() -> None:
    """Every selection of sectors that satisfies the required sectors contains
    the carriers and technologies its elements use.

    An element is part of the model iff all sectors that declare it are
    selected. The smallest valid selection that contains it is therefore its
    declaring sectors plus their (transitively) required sectors; every other
    valid selection that contains it also contains this one. Checking these
    minimal selections covers all valid selections (about 10,000) with a few
    dozen models. Only the carrier attributes are built, so no data is read.
    """
    owners: dict[str, set[str]] = {}
    for sector_cls in _zen_europe_sectors():
        for element_cls in sector_cls().elements:
            owners.setdefault(element_cls.name, set()).add(sector_cls.name)
    selections = {frozenset(_with_required_sectors(o)) for o in owners.values()}

    missing = set()
    for sectors in selections:
        model = _model_with_sectors(sorted(sectors))
        for name, used in _used_elements(model).items():
            for element in used - set(model.elements):
                missing.add(
                    f"{name} (in {sorted(owners[name])}) uses {element} "
                    f"(in {sorted(owners.get(element, []))})"
                )
    assert not missing, (
        "Elements that are missing when only the sectors of the element and "
        "their required sectors are selected:\n" + "\n".join(sorted(missing))
    )


def _with_required_sectors(sectors: set[str]) -> set[str]:
    """Return the sectors and all sectors they require, transitively."""
    result: set[str] = set()
    pending = list(sectors)
    while pending:
        if (sector := pending.pop()) not in result:
            result.add(sector)
            pending += Sector._sector_registry[sector].required_sectors
    return result


def _model_with_sectors(sectors: list[str]) -> Model:
    """Return the default model with only the given sectors (not built)."""
    config = Config.load_from_yaml(DEFAULT_CONFIG_PATH)
    config.source_path = str(DATA_PATH / "raw_data")
    settings = Settings.load_from_yaml(DEFAULT_CONFIG_PATH)
    settings.structure.set_sectors = sectors
    return Model.from_config(config, settings=settings)


def _used_elements(model: Model) -> dict[str, set[str]]:
    """Return the carriers and technologies each element of the model uses: its
    carriers, its base technology and the elements its code reads by name."""
    technologies = model_structure(model)["technologies"]
    used = {}
    for name, element in model.elements.items():
        source = inspect.getsource(type(element))
        used[name] = set(ELEMENT_REFERENCE.findall(source))
        technology = technologies.get(name, {})
        for attribute in CARRIER_ATTRIBUTES:
            used[name].update(technology.get(attribute, []))
        if "base_technology" in technology:
            used[name].add(technology["base_technology"])
    return used

"""Unit tests for storage_technologies module exports and singleton construction."""

from __future__ import annotations

from typing import Any, cast

from zen_creator import StorageTechnology
from zen_creator.model import Model

import zen_europe.elements.storage_technologies as storage_tech_module


def _storage_technology_classes(model: Model) -> list[type[StorageTechnology]]:
    """Return all storage technology classes exported by the module."""
    classes: list[type[StorageTechnology]] = []
    for name in storage_tech_module.__all__:
        storage_tech_cls = getattr(storage_tech_module, name)
        if isinstance(storage_tech_cls, type) and issubclass(
            storage_tech_cls, StorageTechnology
        ):
            classes.append(storage_tech_cls)
    return classes


def _construct_storage_technology(
    storage_tech_cls: type[StorageTechnology], model: Model
) -> StorageTechnology:
    """Construct a storage technology class with the expected constructor signature."""
    storage_tech_factory = cast(type[Any], storage_tech_cls)
    return cast(StorageTechnology, storage_tech_factory(model=model))


def test_all_importable_storage_technologies_are_storage_technology_classes(
    model: Model,
) -> None:
    """All importable module exports must be StorageTechnology subclasses."""
    storage_tech_classes = _storage_technology_classes(model)
    assert storage_tech_classes
    for storage_tech_cls in storage_tech_classes:
        assert issubclass(storage_tech_cls, StorageTechnology)


def test_all_importable_storage_technologies_construct(
    model: Model,
) -> None:
    """All importable storage technologies should construct successfully."""
    for storage_tech_cls in _storage_technology_classes(model):
        storage_tech = _construct_storage_technology(storage_tech_cls, model)
        assert isinstance(storage_tech, storage_tech_cls)
        assert storage_tech_cls.name

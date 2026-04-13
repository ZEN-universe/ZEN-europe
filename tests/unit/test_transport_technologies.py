"""Unit tests for transport_technologies module exports and singleton construction."""

from __future__ import annotations

from typing import Any, cast

from zen_creator import TransportTechnology
from zen_creator.model import Model

import zen_europe.elements.transport_technologies as transport_tech_module


def _transport_technology_classes(model: Model) -> list[type[TransportTechnology]]:
    """Return all transport technology classes exported by the module."""
    classes: list[type[TransportTechnology]] = []
    for name in transport_tech_module.__all__:
        transport_tech_cls = getattr(transport_tech_module, name)
        if isinstance(transport_tech_cls, type) and issubclass(
            transport_tech_cls, TransportTechnology
        ):
            classes.append(transport_tech_cls)
    return classes


def _construct_transport_technology(
    transport_tech_cls: type[TransportTechnology], model: Model
) -> TransportTechnology:
    """Construct a transport technology class."""
    transport_tech_factory = cast(type[Any], transport_tech_cls)
    return cast(TransportTechnology, transport_tech_factory(model=model))


def test_all_importable_transport_technologies_are_transport_technology_classes(
    model: Model,
) -> None:
    """All importable module exports must be TransportTechnology subclasses."""
    transport_tech_classes = _transport_technology_classes(model)
    assert transport_tech_classes
    for transport_tech_cls in transport_tech_classes:
        assert issubclass(transport_tech_cls, TransportTechnology)


def test_all_importable_transport_technologies_construct(
    model: Model,
) -> None:
    """All importable transport technologies should construct successfully."""
    for transport_tech_cls in _transport_technology_classes(model):
        transport_tech = _construct_transport_technology(transport_tech_cls, model)
        assert isinstance(transport_tech, transport_tech_cls)
        assert transport_tech_cls.name

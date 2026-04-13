"""
Unit tests for conversion_technologies module exports and singleton
construction.
"""

from __future__ import annotations

from typing import Any, cast

from zen_creator import ConversionTechnology
from zen_creator.model import Model

import zen_europe.elements.conversion_technologies as conv_tech_module


def _conversion_technology_classes(
    model: Model,
) -> list[type[ConversionTechnology]]:
    """Return all conversion technology classes exported by the module."""
    classes: list[type[ConversionTechnology]] = []
    for name in conv_tech_module.__all__:
        conv_tech_cls = getattr(conv_tech_module, name)
        if isinstance(conv_tech_cls, type) and issubclass(
            conv_tech_cls, ConversionTechnology
        ):
            classes.append(conv_tech_cls)
    return classes


def _construct_conversion_technology(
    conv_tech_cls: type[ConversionTechnology], model: Model
) -> ConversionTechnology:
    """Construct a conversion technology class."""
    conv_tech_factory = cast(type[Any], conv_tech_cls)
    return cast(ConversionTechnology, conv_tech_factory(model=model))


def test_all_importable_conversion_technologies_are_conversion_technology_classes(
    model: Model,
) -> None:
    """All importable module exports must be ConversionTechnology subclasses."""
    conv_tech_classes = _conversion_technology_classes(model)
    assert conv_tech_classes
    for conv_tech_cls in conv_tech_classes:
        assert issubclass(conv_tech_cls, ConversionTechnology)


def test_all_importable_conversion_technologies_construct(
    model: Model,
) -> None:
    """All importable conversion technologies should construct successfully."""
    for conv_tech_cls in _conversion_technology_classes(model):
        conv_tech = _construct_conversion_technology(conv_tech_cls, model)
        assert isinstance(conv_tech, conv_tech_cls)
        assert conv_tech_cls.name

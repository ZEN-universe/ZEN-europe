"""Unit tests for carriers module exports and singleton construction."""

from __future__ import annotations

from typing import Any, cast

from zen_creator.elements import Carrier
from zen_creator.model import Model

import zen_europe.elements.carriers as carriers_module


def _carrier_classes(model: Model) -> list[type[Carrier]]:
    """Return all carrier classes exported by the module."""
    classes: list[type[Carrier]] = []
    for name in carriers_module.__all__:
        carrier_cls = getattr(carriers_module, name)
        if isinstance(carrier_cls, type) and issubclass(carrier_cls, Carrier):
            classes.append(carrier_cls)
    return classes


def _construct_carrier(carrier_cls: type[Carrier], model: Model) -> Carrier:
    """Construct a carrier class with the expected constructor signature."""
    carrier_factory = cast(type[Any], carrier_cls)
    return cast(Carrier, carrier_factory(model=model))


def test_all_importable_carriers_are_carrier_classes(model: Model) -> None:
    """All importable module exports must be Carrier subclasses."""
    carrier_classes = _carrier_classes(model)
    assert carrier_classes
    for carrier_cls in carrier_classes:
        assert issubclass(carrier_cls, Carrier)


def test_all_importable_carriers_construct(model: Model) -> None:
    """All importable carriers should construct successfully."""
    for carrier_cls in _carrier_classes(model):
        carrier = _construct_carrier(carrier_cls, model)
        assert isinstance(carrier, carrier_cls)
        assert carrier_cls.name

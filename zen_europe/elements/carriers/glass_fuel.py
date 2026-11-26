from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator.elements import Carrier

if TYPE_CHECKING:
    from zen_creator.model import Model


class GlassFuel(Carrier):
    """Fuel of the glass furnaces, supplied by the glass fuel retrofits of
    glass_production."""

    name: str = "glass_fuel"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

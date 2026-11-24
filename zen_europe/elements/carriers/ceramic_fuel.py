from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator.elements import Carrier

if TYPE_CHECKING:
    from zen_creator.model import Model


class CeramicFuel(Carrier):
    """Fuel of the ceramic kilns."""

    name: str = "ceramic_fuel"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import ConversionTechnologyConfig, ConversionTechnology, Attribute

class BEVConfig(ConversionTechnologyConfig):
    name: str = "BEV"

class BEV(ConversionTechnology):
    name: str = "BEV"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_capex_specific_conversion(self) -> Attribute:
        """Adds a small penalty CAPEX of 0.01 to avoid over-investment allocation."""
        attr = self.capex_specific_conversion
        attr.default_value = 0.01
        return attr
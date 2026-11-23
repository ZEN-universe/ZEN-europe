from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.food_production_data import (
    FoodProductionData,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class Food(Carrier):
    """Food; demand is today's production."""

    name: str = "food"
    sector: ClassVar[str] = "food"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_demand(self) -> Attribute:
        """Demand from Rehfeldt (2017) and FAOSTAT."""
        return FoodProductionData(self.settings, self.source_path).get_demand(self)


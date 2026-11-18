# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import numpy as np
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class IndustryProduct:
    """Product of an industry heat sector; demand is today's production capacity."""

    sector: ClassVar[str]

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_demand(self) -> Attribute:
        """Demand from JRC-IDEES and FAOSTAT."""
        return IndustryProductionData(self.settings, self.source_path).get_demand(self)

    def _set_availability_export_yearly(self) -> Attribute:
        """Unlimited yearly export."""
        return self.availability_export_yearly.set_data(
            default_value=np.inf,
            unit="tproduct",
            source=AssumptionInformation(description="No export limit."),
        )


class Glass(IndustryProduct, Carrier):
    name: str = "glass"
    sector: ClassVar[str] = "glass"


class Ceramic(IndustryProduct, Carrier):
    name: str = "ceramic"
    sector: ClassVar[str] = "ceramic"


class Paper(IndustryProduct, Carrier):
    name: str = "paper"
    sector: ClassVar[str] = "paper"


class Food(IndustryProduct, Carrier):
    name: str = "food"
    sector: ClassVar[str] = "food"

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import numpy as np
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.ceramic_production_data import (
    CeramicProductionData,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class Ceramic(Carrier):
    """Ceramic; demand is today's production."""

    name: str = "ceramic"
    sector: ClassVar[str] = "ceramic"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_demand(self) -> Attribute:
        """Demand from JRC-IDEES and Rehfeldt (2017)."""
        return CeramicProductionData(self.settings, self.source_path).get_demand(self)


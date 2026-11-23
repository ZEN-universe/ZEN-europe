from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.paper_production_data import (
    PaperProductionData,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class Paper(Carrier):
    """Paper; demand is today's production."""

    name: str = "paper"
    sector: ClassVar[str] = "paper"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_demand(self) -> Attribute:
        """Demand from JRC-IDEES and the JRC BAT reference document."""
        return PaperProductionData(self.settings, self.source_path).get_demand(self)

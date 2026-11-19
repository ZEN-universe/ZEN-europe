from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import Attribute
from zen_creator.elements import Carrier
from zen_creator.datasets.datasets.metadata import AssumptionInformation
if TYPE_CHECKING:
    from zen_creator.model import Model

import numpy as np

class RecoverableWasteHeat(Carrier):
    """Industrial waste heat that can be used in district heating integration"""

    name: str = "recoverable_waste_heat"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_availability_export(self) -> Attribute:
        """Unlimited export."""
        return self.availability_export.set_data(
            default_value=np.inf,
            unit=self.power_unit,
            source=AssumptionInformation(
                description="Allow unlimited export to blow off excess heat."),
        )

    def _set_availability_export_yearly(self) -> Attribute:
        """Unlimited yearly export."""
        return self.availability_export_yearly.set_data(
            default_value=np.inf,
            unit=self.energy_unit,
            source=AssumptionInformation(
                description="Allow unlimited export to blow off excess heat."),
        )

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator import Model

from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute


class Electricity(Carrier):
    """All data and assumption for electricity carrier."""

    name: str = "electricity"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ----Example of optional methods for overriding default attributes ------

    def _set_demand(self) -> Attribute:
        """
        Return the demand of the carrier.

        This method is used to set the self.demand property when the
        model is built. It is optional to implement this method if the
        default value of 0 is suitable for all time steps.
        """
        attr = self.demand
        return attr

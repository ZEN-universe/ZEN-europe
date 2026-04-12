from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import Attribute, TransportTechnology


class PowerLine(TransportTechnology):
    """Class containing all data and assumptions for power line transport technology."""

    name: str = "power_line"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of power line to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of power line.

        Currently set to return the default value. This method can be
        customized to return a specific lifetime for power line.
        """
        attr = self.lifetime
        return attr

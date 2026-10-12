from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.elements import StorageTechnology
from zen_creator.utils.attribute import Attribute


class OilStorage(StorageTechnology):
    """Class containing all data and assumptions for oil storage technology."""

    name: str = "oil_storage"

    # round-trip efficiency, split evenly between charging and discharging
    EFFICIENCY_ROUND_TRIP = 0.995

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of oil storage to oil.
        """
        return Attribute(name="reference_carrier", default_value=["oil"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of oil storage.
        """
        attr = self.lifetime
        return attr.set_data(
            default_value=100,
            source=AssumptionInformation(
                description=(
                    "The lifetime of oil storage is manually set to 100 years, "
                    "so that the tank farms buffering the refinery product "
                    "slate do not retire within the modeling horizon."
                ),
            ),
        )

    def _set_efficiency_charge(self) -> Attribute:
        """
        Sets the charging efficiency of oil storage.
        """
        attr = self.efficiency_charge
        return attr.set_data(
            default_value=np.sqrt(self.EFFICIENCY_ROUND_TRIP),
            source=AssumptionInformation(
                description=(
                    "The round-trip efficiency of oil storage is manually set "
                    f"to {self.EFFICIENCY_ROUND_TRIP} and is split evenly "
                    "between charging and discharging."
                ),
            ),
        )

    def _set_efficiency_discharge(self) -> Attribute:
        """
        Sets the discharging efficiency of oil storage.
        """
        attr = self.efficiency_discharge
        return attr.set_data(
            default_value=np.sqrt(self.EFFICIENCY_ROUND_TRIP),
            source=AssumptionInformation(
                description=(
                    "The round-trip efficiency of oil storage is manually set "
                    f"to {self.EFFICIENCY_ROUND_TRIP} and is split evenly "
                    "between charging and discharging."
                ),
            ),
        )

    def _set_capex_specific_storage(self) -> Attribute:
        """
        Sets the power-specific capex of oil storage.
        """
        attr = self.capex_specific_storage
        return attr.set_data(
            default_value=1,
            unit="Euro/kW",
            source=AssumptionInformation(
                description=(
                    "Oil storage buffers the refinery product slate rather "
                    "than representing a real asset. Its power-specific capex "
                    "is manually set to a nominal 1 Euro/kW to avoid "
                    "over-installation."
                ),
            ),
        )

    def _set_capex_specific_storage_energy(self) -> Attribute:
        """
        Sets the energy-specific capex of oil storage.
        """
        attr = self.capex_specific_storage_energy
        return attr.set_data(
            default_value=1,
            unit="Euro/kWh",
            source=AssumptionInformation(
                description=(
                    "Oil storage buffers the refinery product slate rather "
                    "than representing a real asset. Its energy-specific "
                    "capex is manually set to a nominal 1 Euro/kWh to avoid "
                    "over-installation."
                ),
            ),
        )

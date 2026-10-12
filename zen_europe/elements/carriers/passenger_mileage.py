from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator import Model

from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.passenger_mileage_demand import (
    PassengerMileageDemand,
)
from zen_europe.utils.demand_sensitivity import demand_sensitivity_scenarios


class PassengerMileage(Carrier):
    """All data and assumption for passenger mileage carrier."""

    name: str = "passenger_mileage"

    def __init__(self, model: Model, power_unit: str = "vkm/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ----Example of optional methods for overriding default attributes ------

    def _set_demand(self) -> Attribute:
        """
        Return the demand for passenger mileage.

        """
        passenger_mileage_dataset = PassengerMileageDemand(
            self.settings, self.source_path
        )
        attr = passenger_mileage_dataset.get_demand(self)
        if self.settings.scenario.sensitivity_demand:
            attr.add_scenarios(demand_sensitivity_scenarios(self.name))
        return attr

    def _set_price_shed_demand(self) -> Attribute:
        """
        Return the price of shed demand of the carrier.

        """
        if self.settings.availability.allow_all_demand_shedding:
            return Attribute(
                "price_shed_demand",
                default_value=1e4,
                element=self,
                unit="Euro/vkm",
            )
        else:
            return self.price_shed_demand

    def _set_availability_import(self) -> Attribute:
        """
        Return the availability of import of the carrier.

        """
        return Attribute(
            "availability_import",
            default_value=0,
            element=self,
            unit="vkm/h",
        )

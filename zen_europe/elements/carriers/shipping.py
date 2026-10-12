from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.carrier_availability import (
    CarrierAvailability,
)
from zen_europe.utils.demand_sensitivity import demand_sensitivity_scenarios

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute


class Shipping(Carrier):
    """Shipping carrier class.

    This class implements the specific behavior for the shipping carrier.
    """

    name: str = "shipping"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ----Example of optional methods for overriding default attributes ------

    def _set_availability_import(self) -> Attribute:
        """
        Return the import availability of shipping.

        """
        return Attribute(
            "availability_import",
            default_value=0,
            element=self,
            unit=self.power_unit,
        )

    def _set_price_shed_demand(self) -> Attribute:
        """
        Return the price of shed demand of the carrier.

        """
        if self.settings.availability.allow_all_demand_shedding:
            return Attribute(
                "price_shed_demand",
                default_value=1e4,
                element=self,
                unit="Euro/MWh",
            )
        else:
            return self.price_shed_demand

    def _set_demand(self) -> Attribute:
        """
        Return the demand of shipping.

        """
        carrier_availability = CarrierAvailability(
            settings=self.settings, source_path=self.model.source_path
        )
        attr = carrier_availability.get_shipping_demand(element=self)
        if self.settings.scenario.sensitivity_demand:
            attr.add_scenarios(demand_sensitivity_scenarios(self.name))
        return attr

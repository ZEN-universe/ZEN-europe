from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.methanol_demand import MethanolDemand
from zen_europe.utils.demand_sensitivity import demand_sensitivity_scenarios


class Methanol(Carrier):
    """Methanol carrier class.

    This class implements the specific behavior for the methanol carrier.
    """

    name: str = "methanol"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ----Example of optional methods for overriding default attributes ------

    def _set_availability_import(self) -> Attribute:
        """
        Return the import availability of methanol.

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
        Return the demand of methanol.

        """
        methanol_demand = MethanolDemand(source_path=self.model.source_path)
        attr = methanol_demand.get_methanol_demand(element=self)
        if self.settings.scenario.sensitivity_demand:
            attr.add_scenarios(demand_sensitivity_scenarios(self.name))
        return attr

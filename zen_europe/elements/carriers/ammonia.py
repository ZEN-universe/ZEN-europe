from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.datasets.carrier.ifa import IFA
from zen_europe.utils.demand_sensitivity import demand_sensitivity_scenarios


class Ammonia(Carrier):
    """Ammonia carrier class.

    This class implements the specific behavior for the ammonia carrier.
    """

    name: str = "ammonia"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ----Example of optional methods for overriding default attributes ------

    def _set_demand(self) -> Attribute:
        """
        Return the demand of ammonia.

        """
        ifa = IFA(source_path=self.source_path)
        attr = ifa.get_demand(element=self)
        if self.settings.scenario.sensitivity_demand:
            attr.add_scenarios(demand_sensitivity_scenarios(self.name))
        return attr

    def _set_availability_import(self) -> Attribute:
        """
        Return the import availability of ammonia.

        """
        return Attribute(
            "availability_import",
            default_value=0,
            element=self,
            unit=self.power_unit,
        )

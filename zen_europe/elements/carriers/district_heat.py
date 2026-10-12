from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute


class DistrictHeat(Carrier):
    """District heat carrier class.

    This class implements the specific behavior for the district heat carrier.
    """

    name: str = "district_heat"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ----Example of optional methods for overriding default attributes ------

    def _set_availability_import(self) -> Attribute:
        """
        Return the import availability of district heat.

        """
        return Attribute(
            "availability_import",
            default_value=0,
            element=self,
            unit=self.power_unit,
        )

    def _set_availability_export(self) -> Attribute:
        """
        Return the export availability of district heat.

        """
        return Attribute(
            "availability_export",
            default_value=0,
            element=self,
            unit=self.power_unit,
        )

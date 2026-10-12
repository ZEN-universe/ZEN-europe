from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import AssumptionInformation

from zen_europe.datasets.datasets.financial.ECB import ECBInflation

if TYPE_CHECKING:
    from zen_creator.model import Model

import numpy as np
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.datasets.carrier.tyndp_fuel_prices import TYNDPFuelPrices


class Uranium(Carrier):
    """Uranium carrier class.

    This class implements the specific behavior for the uranium carrier.
    """

    name: str = "uranium"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)
        # set the inflation rate function from the ECB dataset
        # TODO make the inflation rate function directly available in the model,
        # so that it can be used by other elements as well
        ecb_inflation = ECBInflation(source_path=self.source_path)
        self.get_inflation_rate = ecb_inflation.get_inflation_rate

    # ----Example of optional methods for overriding default attributes ------

    def _set_price_import(self) -> Attribute:
        """
        Return the import price of uranium.

        """
        tyndp_fuel_prices = TYNDPFuelPrices(source_path=self.model.source_path)
        return tyndp_fuel_prices.get_price_import(element=self)

    def _set_availability_import(self) -> Attribute:
        """
        Return the availability of uranium.

        """
        attr = self.availability_import
        return attr.set_data(
            default_value=np.inf,
            df=None,
            source=AssumptionInformation(
                description=(
                    "The import availability of uranium is set to infinity, "
                    "as the availability is not capped in the settings."
                )
            ),
        )

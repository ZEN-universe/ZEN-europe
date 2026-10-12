from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import AssumptionInformation

from zen_europe.datasets.dataset_collections.carrier_availability import (
    CarrierAvailability,
)
from zen_europe.datasets.datasets.carrier.ipcc_emission_factors import (
    IPCCEmissionFactors,
)
from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation

if TYPE_CHECKING:
    from zen_creator.model import Model

import numpy as np
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.datasets.carrier.bnef_fuelprices import BNEFFuelPrices


class HardCoal(Carrier):
    """Hard coal carrier class.

    This class implements the specific behavior for the hard coal carrier.
    """

    name: str = "hard_coal"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)
        # set the inflation rate function from the ECB dataset
        # TODO make the inflation rate function directly available in the model,
        # so that it can be used by other elements as well
        ecb_inflation = ECBInflation(source_path=self.source_path)
        self.get_inflation_rate = ecb_inflation.get_inflation_rate
        ecb_dollar2euro = ECBDollar2Euro(source_path=self.source_path)
        self.get_dollar2euro = ecb_dollar2euro.get_dollar2euro

    # ----Example of optional methods for overriding default attributes ------

    def _set_availability_import(self) -> Attribute:
        """
        Return the import availability of hard coal.

        """
        if self.settings.availability.cap_coal_import:
            carrier_availability = CarrierAvailability(
                settings=self.settings, source_path=self.model.source_path
            )
            return carrier_availability.get_coal_availability(element=self)
        else:
            attr = self.availability_import
            return attr.set_data(
                default_value=np.inf,
                df=None,
                source=AssumptionInformation(
                    description=(
                        "The import availability of hard coal is set to infinity, "
                        "as the availability is not capped in the settings."
                    )
                ),
            )

    def _set_price_import(self) -> Attribute:
        """
        Return the import price of hard coal.

        """
        bnef_fuel_prices = BNEFFuelPrices(source_path=self.model.source_path)
        return bnef_fuel_prices.get_price_import(element=self)

    def _set_carbon_intensity_carrier_import(self) -> Attribute:
        """
        Return the carbon intensity of hard coal.

        """
        ipcc_emission_factors = IPCCEmissionFactors(source_path=self.model.source_path)
        return ipcc_emission_factors.get_carbon_intensity(element=self)

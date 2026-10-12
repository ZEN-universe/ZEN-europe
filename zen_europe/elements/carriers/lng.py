from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.lng_availability import LNGAvailability
from zen_europe.datasets.datasets.carrier.bnef_fuelprices import BNEFFuelPrices
from zen_europe.datasets.datasets.carrier.ipcc_emission_factors import (
    IPCCEmissionFactors,
)
from zen_europe.datasets.datasets.financial.ECB import ECBDollar2Euro, ECBInflation

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute


class LNG(Carrier):
    """LNG carrier class.

    This class implements the specific behavior for the LNG carrier.
    """

    name: str = "lng"

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
        Return the import availability of LNG.

        """
        lng_availability = LNGAvailability(source_path=self.model.source_path)
        return lng_availability.get_availability_import(element=self)

    def _set_price_import(self) -> Attribute:
        """
        Return the import price of LNG.

        """
        bnef_fuel_prices = BNEFFuelPrices(source_path=self.model.source_path)
        return bnef_fuel_prices.get_price_import(
            element=self, manual_carrier_name="natural_gas"
        )

    def _set_carbon_intensity_carrier_import(self) -> Attribute:
        """
        Return the carbon intensity of LNG.

        """
        ipcc_emission_factors = IPCCEmissionFactors(source_path=self.model.source_path)
        return ipcc_emission_factors.get_carbon_intensity(element=self)

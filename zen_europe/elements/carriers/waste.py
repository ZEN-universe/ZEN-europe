from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import AssumptionInformation

from zen_europe.datasets.dataset_collections.carrier_availability import (
    CarrierAvailability,
)
from zen_europe.datasets.datasets.carrier.ipcc_emission_factors import (
    IPCCEmissionFactors,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

import numpy as np
from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute


class Waste(Carrier):
    """Waste carrier class.

    This class implements the specific behavior for the waste carrier.
    """

    name: str = "waste"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ----Example of optional methods for overriding default attributes ------

    def _set_availability_import(self) -> Attribute:
        """
        Return the import availability of waste.

        """
        if self.settings.availability.cap_waste_import:
            include_industry = "cement" in self.model.sectors
            carrier_availability = CarrierAvailability(
                settings=self.settings, source_path=self.model.source_path
            )
            return carrier_availability.get_waste_availability(
                element=self, include_industry=include_industry
            )
        else:
            attr = self.availability_import
            return attr.set_data(
                default_value=np.inf,
                df=None,
                source=AssumptionInformation(
                    description=(
                        "The import availability of waste is set to infinity, "
                        "as the availability is not capped in the settings."
                    )
                ),
            )

    def _set_price_import(self) -> Attribute:
        """
        Return the import price of waste.

        """
        return Attribute(
            "price_import",
            default_value=0,
            element=self,
            unit="Euro/MWh",
        )

    def _set_carbon_intensity_carrier_import(self) -> Attribute:
        """
        Return the carbon intensity of waste.

        """
        ipcc_emission_factors = IPCCEmissionFactors(source_path=self.model.source_path)
        return ipcc_emission_factors.get_carbon_intensity(element=self)

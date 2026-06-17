from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator import Model

from zen_creator import Attribute, Carrier, CarrierConfig

from zen_europe.datasets.datasets.carriers.biomass.enspreso import ENSPRESO


class WetBiomassConfig(CarrierConfig):
    name: str = "wet_biomass"
    type: str = "WetBiomassConfig"
    scenario: str = "ENS_Med"


class WetBiomass(Carrier):
    """Class containing all data for the wet_biomass carrier."""

    name: str = "wet_biomass"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ----Example of optional methods for overriding default attributes ------

    def _set_availability_import(self) -> Attribute:
        """
        Return the availability import of the carrier.

        This method is used to set the self.availability_import property when
        the  model is built.
        """
        attr = self.availability_import

        attr = ENSPRESO(self.model.source_path).get_availability_import(element=self)
        return attr

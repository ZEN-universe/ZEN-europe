from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator import Model

from zen_creator.elements import Carrier
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.datasets.carrier.enspreso_biomass import (
    EnspresoBiomassAvailability,
    EnspresoBiomassPrice,
)
from zen_europe.datasets.datasets.financial.ECB import ECBInflation


class WetBiomass(Carrier):
    """All data and assumptions for the wet biomass carrier."""

    name: str = "wet_biomass"

    # solid-biomass ENSPRESO energy-commodity codes
    _biomass_types = [
        "MINBIOGAS1",  # Manure solid, liquid
        "MINBIOSLU1",  # sludge
    ]

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)
        # set the inflation rate function from the ECB dataset
        # TODO make the inflation rate function directly available in the model,
        # so that it can be used by other elements as well
        ecb = ECBInflation(source_path=self.source_path)
        self.get_inflation_rate = ecb.get_inflation_rate

    # ----Example of optional methods for overriding default attributes ------

    def _set_availability_import(self) -> Attribute:
        """Return the import availability of wetbiomass from ENSPRESO potentials."""
        if self.settings.availability.annual_cap_biomass_import:
            return self.availability_import

        enspreso = EnspresoBiomassAvailability(self.source_path)
        attr = enspreso.get_availability_import(
            element=self, biomass_types=self._biomass_types
        )
        if self.settings.scenario.sensitivity_biomass:
            attr.add_scenarios(
                [
                    enspreso.get_availability_import_scenario(
                        element=self,
                        biomass_types=self._biomass_types,
                        name="biomass_low",
                        ens_scenario="ENS_Low",
                        suffix="low",
                    ),
                    enspreso.get_availability_import_scenario(
                        element=self,
                        biomass_types=self._biomass_types,
                        name="biomass_high",
                        ens_scenario="ENS_High",
                        suffix="high",
                    ),
                ]
            )
        return attr

    def _set_availability_import_yearly(self) -> Attribute:
        """Return the import availability of wet biomass from ENSPRESO potentials."""
        if self.settings.availability.annual_cap_biomass_import:
            enspreso = EnspresoBiomassAvailability(self.source_path)
            return enspreso.get_availability_import_yearly(
                element=self, biomass_types=self._biomass_types
            )
        else:
            return self.availability_import_yearly

    def _set_price_import(self) -> Attribute:
        """Return the import price of wet biomass from ENSPRESO potentials."""
        enspreso = EnspresoBiomassPrice(self.source_path)
        return enspreso.get_price_import(
            element=self,
            biomass_types=self._biomass_types,
            regional_prices=self.settings.cost.use_nodal_biomass_prices,
        )

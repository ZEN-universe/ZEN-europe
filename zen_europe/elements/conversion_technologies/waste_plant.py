from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.lifetime_expectation import (
    LifetimeExpectation,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.financial.potencia import Potencia
from zen_europe.datasets.datasets.technology.powerplantmatching import (
    PowerPlantMatching,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)


class WastePlant(ConversionTechnology):
    """Class containing all data and assumptions for waste plants."""

    name: str = "waste_plant"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of waste plants to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of waste plants to waste.
        """
        return Attribute(name="input_carrier", default_value=["waste"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of waste plants to electricity.
        """
        return Attribute(
            name="output_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of waste plants.

        """
        lifetime_expectation = LifetimeExpectation(
            settings=self.settings, source_path=self.source_path
        )
        return lifetime_expectation.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of waste plants.

        """
        if self.settings.investment.use_construction_times:
            tech_db = TechnologyCostDatabase(
                settings=self.settings, source_path=self.source_path
            )
            return tech_db.get_construction_time(self)
        else:
            return self.construction_time

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of waste plants.

        """
        eurostat_db = Eurostat(settings=self.settings, source_path=self.source_path)
        efficiencies = eurostat_db.get_efficiencies()
        efficiency = efficiencies.get(self.name, None)
        if efficiency is None:
            raise ValueError(
                f"Efficiency for {self.name} is not available in the Eurostat dataset."
            )
        conversion_factor = [
            {
                "waste": {"default_value": 1 / efficiency, "unit": "GWh/GWh"},
            }
        ]
        attr = self.conversion_factor
        attr.set_data(
            default_value=conversion_factor,
            source=SourceInformation(
                description=(
                    "The conversion factor is derived from the Eurostat dataset as "
                    "the total consumption of waste divided by "
                    "the total electricity generation from waste plants."
                ),
                metadata=eurostat_db.metadata,
            ),
        )
        return attr

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for waste plants.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for waste plants.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for waste plants.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for waste plants.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            powerplantmatching = PowerPlantMatching(source_path=self.source_path)
            return powerplantmatching.get_capacity_existing(self)
        else:
            attr = self.capacity_existing
            attr.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description=("We do not consider existing capacities."),
                ),
            )
            return attr

    def _set_max_load(self) -> Attribute:
        """
        Sets the maximum load for waste plants.

        Returns:
            Attribute: An Attribute object containing the maximum load data.
        """
        potencia_db = Potencia(source_path=self.source_path)
        return potencia_db.get_max_load(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of waste plant.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

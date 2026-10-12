from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.lifetime_expectation import (
    LifetimeExpectation,
)
from zen_europe.datasets.dataset_collections.potential_capacity_renewables import (
    PotentialCapacityRenewables,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.technology.pan_european_climate_database import (
    PanEuropeanClimateDatabase,
)
from zen_europe.datasets.datasets.technology.powerplantmatching import (
    PowerPlantMatching,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import AssumptionInformation, Attribute, ConversionTechnology


class WindOnshore(ConversionTechnology):
    """Class containing all data and assumptions for wind onshore."""

    name: str = "wind_onshore"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of wind onshore to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of wind onshore to an empty list.

        This is because wind onshore do not have an input carrier,
        as they convert wind energy directly into electricity.
        """
        return Attribute(name="input_carrier", default_value=[], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of wind onshore to electricity.
        """
        return Attribute(
            name="output_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of wind onshore.

        """
        lifetime_expectation = LifetimeExpectation(
            settings=self.settings, source_path=self.source_path
        )
        return lifetime_expectation.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of wind onshore.

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
        Return the conversion factor of wind onshore.

        The conversion factor is empty, as wind onshore has no input carrier.
        """
        attr = self.conversion_factor
        return attr.set_data(
            default_value=[],
            source=AssumptionInformation(
                description=(
                    "The conversion factor of wind onshore is manually set to an "
                    "empty list, as it has no input carrier."
                ),
            ),
        )

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for wind onshore.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for wind onshore.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for wind onshore.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_limit(self) -> Attribute:
        """
        Sets the capacity limit for wind onshore.

        Returns:
            Attribute: An Attribute object containing the capacity limit data.
        """
        pcr = PotentialCapacityRenewables(source_path=self.source_path)
        return pcr.get_capacity_limit(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for wind onshore.

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
        Sets the maximum load for wind onshore.

        Returns:
            Attribute: An Attribute object containing the maximum load data.
        """
        pecd = PanEuropeanClimateDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return pecd.get_max_load(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of wind onshore.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
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

from zen_europe.datasets.dataset_collections.heat_demand import HeatDemand


class BiomassBoilerDH(ConversionTechnology):
    """Class containing all data and assumptions for district heating biomass
    boilers."""

    name: str = "biomass_boiler_DH"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of district heating biomass boilers to district_heat.
        """
        return Attribute(
            name="reference_carrier", default_value=["district_heat"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of district heating biomass boilers to biomass.
        """
        return Attribute(name="input_carrier", default_value=["biomass"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of district heating biomass boilers to district_heat.
        """
        return Attribute(
            name="output_carrier", default_value=["district_heat"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of district heating biomass boilers.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of district heating biomass boilers.

        """
        attr = self.conversion_factor
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        eff, agencies = tech_db.get_efficiency(self)
        eff = eff.loc[self.settings.time.reference_year]
        cf = [{"biomass": {"default_value": 1 / eff, "unit": "GW/GW"}}]
        source = SourceInformation(
            description=(
                "The conversion factor of district heating biomass boilers is based on "
                f"data from {', '.join(agencies)}. "
            ),
            metadata=tech_db.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of district heating biomass boilers.

        """
        if self.settings.investment.use_construction_times:
            tech_db = TechnologyCostDatabase(
                settings=self.settings, source_path=self.source_path
            )
            return tech_db.get_construction_time(self)
        else:
            return self.construction_time

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for district heating biomass
        boilers.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for district heating
        biomass boilers.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for district heating
        biomass boilers.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for district heating biomass boilers.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            heat_demand_dataset = HeatDemand(
                settings=self.settings, source_path=self.source_path
            )
            return heat_demand_dataset.get_capacity_existing(self, is_dh=True)
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

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of biomass boiler DH.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

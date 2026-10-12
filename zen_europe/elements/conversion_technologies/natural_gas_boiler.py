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


class NaturalGasBoiler(ConversionTechnology):
    """Class containing all data and assumptions for natural gas boilers."""

    name: str = "natural_gas_boiler"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of natural gas boilers to heat.
        """
        return Attribute(name="reference_carrier", default_value=["heat"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of natural gas boilers to natural gas.
        """
        return Attribute(
            name="input_carrier", default_value=["natural_gas"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of natural gas boilers to heat.
        """
        return Attribute(name="output_carrier", default_value=["heat"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of natural gas boilers.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of natural gas boilers.

        """
        attr = self.conversion_factor
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        eff, agencies = tech_db.get_efficiency(self)
        eff = eff.loc[self.settings.time.reference_year]
        cf = [{"natural_gas": {"default_value": 1 / eff, "unit": "GW/GW"}}]
        source = SourceInformation(
            description=(
                "The conversion factor of natural gas boilers is based on data from "
                f"{', '.join(agencies)}. "
            ),
            metadata=tech_db.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of natural gas boilers.

        """
        if self.settings.investment.use_construction_times:
            attr = self.construction_time
            source = AssumptionInformation(
                description=(
                    "The construction time of natural gas boilers is assumed to be 0 "
                    "years, as they can be installed quickly and do not require "
                    "extensive construction work."
                )
            )
            attr.set_data(default_value=0, source=source)
            return attr
        else:
            return self.construction_time

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for natural gas boilers.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for natural gas boilers.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for natural gas
        boilers.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for natural gas boilers.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            heat_demand_dataset = HeatDemand(
                settings=self.settings, source_path=self.source_path
            )
            return heat_demand_dataset.get_capacity_existing(self)
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
        Sets the maximum load for natural gas boilers.

        Returns:
            Attribute: An Attribute object containing the maximum load data.
        """
        heat_demand_dataset = HeatDemand(
            settings=self.settings, source_path=self.source_path
        )

        return heat_demand_dataset.get_max_load(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of natural gas boiler.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

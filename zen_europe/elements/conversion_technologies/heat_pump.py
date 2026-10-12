from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.carrier.when2heat import When2Heat
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


class HeatPump(ConversionTechnology):
    """Class containing all data and assumptions for heat pumps."""

    name: str = "heat_pump"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of heat pumps to heat.
        """
        return Attribute(name="reference_carrier", default_value=["heat"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of heat pumps to electricity.
        """
        return Attribute(
            name="input_carrier", default_value=["electricity"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of heat pumps to heat.
        """
        return Attribute(name="output_carrier", default_value=["heat"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of heat pumps.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of heat pumps.

        """
        attr = self.conversion_factor
        when2heat_dataset = When2Heat(
            settings=self.settings, source_path=self.source_path
        )
        cop_data = when2heat_dataset.get_COP()
        cop = cop_data.xs("floor", level=1, axis=1)
        cop.index.name = "time"
        cf = [
            {"electricity": {"default_value": 1 / cop.mean().mean(), "unit": "GW/GW"}}
        ]
        source = SourceInformation(
            description=(
                "The conversion factor of heat pumps is based on data from When2Heat. "
                "We assume that the heat pump shows the COP of a floor heat pump."
            ),
            metadata=when2heat_dataset.metadata,
        )
        attr.set_data(default_value=cf, df=1 / cop, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of heat pumps.

        """
        if self.settings.investment.use_construction_times:
            attr = self.construction_time
            source = AssumptionInformation(
                description=(
                    "The construction time of heat pumps is assumed to be 0 years, as "
                    "they can be installed quickly and do not require extensive "
                    "construction work."
                )
            )
            attr.set_data(default_value=0, source=source)
            return attr
        else:
            return self.construction_time

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for heat pumps.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for heat pumps.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for heat pumps.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for heat pumps.

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
        Sets the maximum load for heat pumps.

        Returns:
            Attribute: An Attribute object containing the maximum load data.
        """
        heat_demand_dataset = HeatDemand(
            settings=self.settings, source_path=self.source_path
        )

        return heat_demand_dataset.get_max_load(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of heat pump.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

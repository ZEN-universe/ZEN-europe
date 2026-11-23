from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import (
    AssumptionInformation,
    SourceInformation,
)
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_heat_supply import (
    IndustryHeatSupply,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class CoalBoilerIndustry(ConversionTechnology):
    """Industrial hard coal boiler supplying the 150-200 °C band."""

    name: str = "coal_boiler_industry"
    fuel: ClassVar[str] = "coal"
    # technology the diffusion rate is taken from
    diffusion_proxy: ClassVar[str] = "hard_coal_boiler_DH"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Heat of the 150-200 °C band."""
        return Attribute(
            "reference_carrier", default_value=["heat_industry_150_200"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Hard coal."""
        return Attribute("input_carrier", default_value=["hard_coal"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """Heat of the 150-200 °C band."""
        return Attribute(
            "output_carrier", default_value=["heat_industry_150_200"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Inverse of the DEA efficiency."""
        tech_db = TechnologyCostDatabase(self.settings, self.source_path)
        efficiency, agencies = tech_db.get_efficiency(self)
        efficiency = efficiency.loc[self.settings.time.reference_year]
        return self.conversion_factor.set_data(
            default_value=[
                {"hard_coal": {"default_value": 1 / efficiency, "unit": "GW/GW"}}
            ],
            source=SourceInformation(
                description=(
                    f"Inverse of the efficiency of '{self.name}' "
                    f"from {', '.join(agencies)}."
                ),
                metadata=tech_db.metadata,
            ),
        )

    def _set_lifetime(self) -> Attribute:
        """Lifetime from DEA."""
        return TechnologyCostDatabase(self.settings, self.source_path).get_lifetime(
            self
        )

    def _set_construction_time(self) -> Attribute:
        """Construction time from DEA."""
        if not self.settings.investment.use_construction_times:
            return self.construction_time
        return TechnologyCostDatabase(
            self.settings, self.source_path
        ).get_construction_time(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """Investment cost from DEA."""
        return TechnologyCostDatabase(
            self.settings, self.source_path
        ).get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """Fixed O&M cost from DEA."""
        return TechnologyCostDatabase(
            self.settings, self.source_path
        ).get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """Variable O&M cost from DEA."""
        return TechnologyCostDatabase(
            self.settings, self.source_path
        ).get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """Today's heat demand of the industry heat sectors, split by fuel."""
        if not self.settings.investment.use_existing_capacities:
            return self.capacity_existing.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description="We do not consider existing capacities."
                ),
            )
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_capacity_existing_boiler(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """Max diffusion rate of the district heating boiler."""
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        return TechnologyDiffusionMannhardt(
            source_path=self.source_path
        ).get_max_diffusion_rate(self, proxy_element_name=self.diffusion_proxy)

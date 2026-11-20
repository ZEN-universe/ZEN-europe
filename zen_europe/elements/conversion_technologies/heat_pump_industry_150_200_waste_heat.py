from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
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


class HeatPumpIndustry150200WasteHeat(ConversionTechnology):
    """Industrial heat pump for 150-200 °C on waste heat."""

    name: str = "heat_pump_industry_150_200_waste_heat"
    temp_level: ClassVar[str] = "150_200"
    heat_source: ClassVar[str] = "waste_heat"
    # DEA technology the costs, lifetime and construction time are taken from
    cost_proxy: ClassVar[str] = "heat_pump_industry_150"
    # technology the diffusion rate is taken from
    diffusion_proxy: ClassVar[str] = "heat_pump_DH"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Heat of the 150-200 °C band."""
        return Attribute(
            "reference_carrier", default_value=["heat_industry_150_200"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Electricity and recoverable waste heat."""
        return Attribute(
            "input_carrier",
            default_value=["electricity", "recoverable_waste_heat"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """Heat of the 150-200 °C band."""
        return Attribute(
            "output_carrier", default_value=["heat_industry_150_200"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Electricity per heat (1/COP of Bever et al. (2024)) and recoverable waste
        heat per heat (1 - 1/COP)."""
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_conversion_factor_heat_pump_waste_heat(self)

    def _set_lifetime(self) -> Attribute:
        """Lifetime from DEA."""
        return TechnologyCostDatabase(self.settings, self.source_path).get_lifetime(
            self, proxy_element_name=self.cost_proxy
        )

    def _set_construction_time(self) -> Attribute:
        """Construction time from DEA."""
        if not self.settings.investment.use_construction_times:
            return self.construction_time
        return TechnologyCostDatabase(
            self.settings, self.source_path
        ).get_construction_time(self, proxy_element_name=self.cost_proxy)

    def _set_capex_specific_conversion(self) -> Attribute:
        """Investment cost from DEA, plus waste-heat recovery."""
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_capex_specific_conversion_heat_pump_waste_heat(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """Fixed O&M cost from DEA."""
        return TechnologyCostDatabase(
            self.settings, self.source_path
        ).get_opex_specific_fixed(self, proxy_element_name=self.cost_proxy)

    def _set_opex_specific_variable(self) -> Attribute:
        """Variable O&M cost from DEA."""
        return TechnologyCostDatabase(
            self.settings, self.source_path
        ).get_opex_specific_variable(self, proxy_element_name=self.cost_proxy)

    def _set_capacity_existing(self) -> Attribute:
        """No industrial heat pumps today."""
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_capacity_existing_heat_pump(self)

    def _set_capacity_addition_unbounded(self) -> Attribute:
        """Seed from the existing district heating heat pumps."""
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_capacity_addition_unbounded_heat_pump(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """Max diffusion rate of the district heating heat pump."""
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        return TechnologyDiffusionMannhardt(
            source_path=self.source_path
        ).get_max_diffusion_rate(self, proxy_element_name=self.diffusion_proxy)

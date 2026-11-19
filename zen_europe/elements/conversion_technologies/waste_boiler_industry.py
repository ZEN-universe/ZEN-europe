from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_heat_supply import (
    IndustryHeatSupply,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class WasteBoilerIndustry(ConversionTechnology):
    """Industrial waste boiler supplying the 150-200 °C band. No DEA data:
    efficiency, lifetime and costs as the DH waste boiler."""

    name: str = "waste_boiler_industry"
    fuel: ClassVar[str] = "waste"
    # technology the diffusion rate is taken from
    diffusion_proxy: ClassVar[str] = "waste_boiler_DH"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Heat of the 150-200 °C band."""
        return Attribute(
            "reference_carrier", default_value=["heat_industry_150_200"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Waste."""
        return Attribute("input_carrier", default_value=["waste"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """Heat of the 150-200 °C band."""
        return Attribute(
            "output_carrier", default_value=["heat_industry_150_200"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("conversion_factor")

    def _set_lifetime(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("lifetime")

    def _set_construction_time(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("construction_time")

    def _set_capex_specific_conversion(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("capex_specific_conversion")

    def _set_opex_specific_fixed(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("opex_specific_fixed")

    def _set_opex_specific_variable(self) -> Attribute:
        """As waste_boiler_DH."""
        return self._as_dh_boiler("opex_specific_variable")

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

    def _as_dh_boiler(self, name: str) -> Attribute:
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_attribute_waste_boiler(self, name)

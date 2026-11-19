from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import RetrofittingTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.ceramic_production_data import (
    CeramicProductionData,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class CeramicPostComb(RetrofittingTechnology):
    """Post-combustion capture of the ceramic kilns' process CO2, as
    cement_post_comb."""

    name: str = "ceramic_post_comb"
    base_technology_name: str = "ceramic_production"
    sector: ClassVar[str] = "ceramic"
    # costs, lifetime, construction time and diffusion of the same DEA capture unit
    # as the cement kiln
    cost_proxy: ClassVar[str] = "cement_post_comb"
    diffusion_proxy: ClassVar[str] = "cement_post_comb"

    def __init__(self, model: Model, power_unit: str = "tCO2/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Captured carbon."""
        return Attribute("reference_carrier", default_value=["carbon"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """Heat from natural gas and electricity."""
        return Attribute(
            "input_carrier",
            default_value=["natural_gas", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """Captured carbon and recoverable waste heat."""
        return Attribute(
            "output_carrier",
            default_value=["carbon", "recoverable_waste_heat"],
            element=self,
        )

    def _set_retrofit_reference_carrier(self) -> Attribute:
        """Captured carbon."""
        return Attribute(
            "retrofit_reference_carrier", default_value=["carbon"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Capture unit from DEA, heat from the ceramic fuels."""
        return CeramicProductionData(
            self.settings, self.source_path
        ).get_conversion_factor_post_comb(self)

    def _set_retrofit_flow_coupling_factor(self) -> Attribute:
        """Process emissions of ceramic times the capture rate."""
        return CeramicProductionData(
            self.settings, self.source_path
        ).get_retrofit_flow_coupling_factor_post_comb(self)

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
        """Investment cost from DEA."""
        return TechnologyCostDatabase(
            self.settings, self.source_path
        ).get_capex_specific_conversion(self, proxy_element_name=self.cost_proxy)

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

    def _set_carbon_intensity_technology(self) -> Attribute:
        """No own emissions."""
        return self.carbon_intensity_technology.set_data(
            default_value=0.0,
            unit="ton/tCO2",
            source=AssumptionInformation(description="No own emissions."),
        )

    def _set_capacity_addition_unbounded(self) -> Attribute:
        """As cement_post_comb."""
        cement = self.model.elements["cement_post_comb"].capacity_addition_unbounded
        return self.capacity_addition_unbounded.set_data(
            default_value=cement.default_value,
            unit=cement.unit,
            source=AssumptionInformation(description="As cement_post_comb."),
        )

    def _set_max_diffusion_rate(self) -> Attribute:
        """Max diffusion rate of cement_post_comb."""
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        return TechnologyDiffusionMannhardt(
            source_path=self.source_path
        ).get_max_diffusion_rate(self, proxy_element_name=self.diffusion_proxy)

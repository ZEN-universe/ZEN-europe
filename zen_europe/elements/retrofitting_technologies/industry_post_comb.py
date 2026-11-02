# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import RetrofittingTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)
from zen_europe.elements.conversion_technologies.industry_heat_technology import (
    IndustryHeatTechnology,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class IndustryPostComb(IndustryHeatTechnology):
    """Post-combustion capture of a kiln's process CO2, as cement_post_comb."""

    # costs and diffusion of the same DEA capture unit as the cement kiln
    cost_proxy: ClassVar[str] = "cement_post_comb"
    diffusion_proxy: ClassVar[str] = "cement_post_comb"

    def __init__(self, model: Model, power_unit: str = "tCO2/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Captured carbon."""
        return Attribute("reference_carrier", default_value=["carbon"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """Heat from natural gas and coal, electricity."""
        return Attribute(
            "input_carrier",
            default_value=["natural_gas", "hard_coal", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """Captured carbon and waste heat."""
        return Attribute(
            "output_carrier", default_value=["carbon", "district_heat"], element=self
        )

    def _set_retrofit_reference_carrier(self) -> Attribute:
        """Captured carbon."""
        return Attribute(
            "retrofit_reference_carrier", default_value=["carbon"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Capture unit from DEA, heat from the sector's fuels."""
        return self._data().get_conversion_factor_post_comb(self)

    def _set_retrofit_flow_coupling_factor(self) -> Attribute:
        """Process emissions times the capture rate."""
        return self._data().get_retrofit_flow_coupling_factor(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """Investment cost from DEA."""
        return self._cost_db().get_capex_specific_conversion(
            self, proxy_element_name=self.cost_proxy
        )

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

    def _data(self) -> IndustryProductionData:
        return IndustryProductionData(self.settings, self.source_path)


class GlassPostComb(IndustryPostComb, RetrofittingTechnology):
    name: str = "glass_post_comb"
    base_technology_name: str = "glass_production"
    sector: ClassVar[str] = "glass"


class CeramicPostComb(IndustryPostComb, RetrofittingTechnology):
    name: str = "ceramic_post_comb"
    base_technology_name: str = "ceramic_production"
    sector: ClassVar[str] = "ceramic"

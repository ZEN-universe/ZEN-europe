from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import Attribute, RetrofittingTechnology

from zen_europe.datasets.dataset_collections.glass_production_data import (
    GlassProductionData,
)
from zen_europe.datasets.dataset_collections.industrial_waste_heat import (
    IndustrialWasteHeat,
)
from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)
from zen_europe.datasets.datasets.carrier.aidres import Aidres
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class HydrogenToGlassFuel(RetrofittingTechnology):
    """Hydrogen firing of the glass furnaces."""

    name: str = "hydrogen_to_glass_fuel"
    base_technology_name: str = "glass_production"
    sector: ClassVar[str] = "glass"
    fuel: ClassVar[str] = "hydrogen"
    # technology the diffusion rate is taken from
    diffusion_proxy: ClassVar[str] = "hydrogen_to_cement_fuel"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Glass fuel."""
        return Attribute(
            "reference_carrier", default_value=["glass_fuel"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Hydrogen."""
        return Attribute("input_carrier", default_value=["hydrogen"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """Glass fuel and the waste heat of the furnace."""
        return Attribute(
            "output_carrier",
            default_value=["glass_fuel", *self.settings.operation.waste_heat_carriers],
            element=self,
        )

    def _set_retrofit_reference_carrier(self) -> Attribute:
        """Glass fuel."""
        return Attribute(
            "retrofit_reference_carrier", default_value=["glass_fuel"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """As glass_production."""
        return IndustryProductionData(
            self.settings, self.source_path
        ).get_lifetime_fuel_retrofit(self)

    def _set_conversion_factor(self) -> Attribute:
        """Hydrogen per glass fuel of the AIDRES hydrogen routes, plus the waste heat
        from sEEnergies."""
        return IndustrialWasteHeat(
            self.settings, self.source_path
        ).get_conversion_factor_kiln_fuel(self)

    def _set_retrofit_flow_coupling_factor(self) -> Attribute:
        """The whole glass fuel demand."""
        return GlassProductionData(
            self.settings, self.source_path
        ).get_retrofit_flow_coupling_factor_fuel(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """No capex: AIDRES capex as the natural gas routes."""
        return Aidres(self.source_path).get_capex_specific_conversion_glass_fuel(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """Max diffusion rate of hydrogen_to_cement_fuel."""
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        return TechnologyDiffusionMannhardt(
            source_path=self.source_path
        ).get_max_diffusion_rate(self, proxy_element_name=self.diffusion_proxy)

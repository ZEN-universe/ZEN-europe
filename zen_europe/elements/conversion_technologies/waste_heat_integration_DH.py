from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)

from zen_europe.datasets.datasets.technology.stark2025 import Stark2025
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class WasteHeatIntegrationDH(ConversionTechnology):
    """Feed-in of recoverable waste heat into the district heating grid."""

    name: str = "waste_heat_integration_DH"
    # technology the lifetime is taken from
    lifetime_proxy: ClassVar[str] = "district_heating_grid"
    # technology the diffusion rate is taken from
    diffusion_proxy: ClassVar[str] = "heat_pump_DH"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """District heat."""
        return Attribute(
            "reference_carrier", default_value=["district_heat"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Recoverable waste heat."""
        return Attribute(
            "input_carrier", default_value=["recoverable_waste_heat"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """District heat."""
        return Attribute(
            "output_carrier", default_value=["district_heat"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Lossless."""
        return self.conversion_factor.set_data(
            default_value=[
                {"recoverable_waste_heat": {"default_value": 1.0, "unit": "GW/GW"}}
            ],
            source=AssumptionInformation(
                description="Lossless heat transfer into the district heating grid."
            ),
        )

    def _set_lifetime(self) -> Attribute:
        """Lifetime of the district heating grid."""
        proxy = self.model.conversion_technologies[self.lifetime_proxy].lifetime
        return self.lifetime.set_data(
            default_value=proxy.default_value,
            source=AssumptionInformation(
                description=(
                    f"Lifetime of '{self.lifetime_proxy}', as the connection to the "
                    "grid is mostly piping."
                )
            ),
        )

    def _set_capex_specific_conversion(self) -> Attribute:
        """Waste-heat recovery of Stark et al. (2025)."""
        stark = Stark2025(self.source_path)
        price_year = self.settings.time.price_year
        capex = stark.get_capex_waste_heat_recovery(price_year)
        return self.capex_specific_conversion.set_data(
            default_value=capex,
            unit="Euro/kW",
            source=SourceInformation(
                description=(
                    "The waste-heat recovery of 1,788 USD/kWth (2025 USD) in Stark et "
                    f"al. (2025), converted to {capex:.0f} Euro/kW ({price_year} Euro) "
                    "with the ECB dollar-to-euro exchange rate of 2025 and the ECB "
                    "inflation."
                ),
                metadata=stark.metadata,
            ),
        )

    def _set_max_diffusion_rate(self) -> Attribute:
        """Max diffusion rate of the district heating heat pump."""
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        return TechnologyDiffusionMannhardt(
            source_path=self.source_path
        ).get_max_diffusion_rate(self, proxy_element_name=self.diffusion_proxy)

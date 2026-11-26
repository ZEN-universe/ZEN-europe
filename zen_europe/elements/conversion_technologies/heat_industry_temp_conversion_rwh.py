from __future__ import annotations

from typing import TYPE_CHECKING

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_heat_supply import (
    IndustryHeatSupply,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class HeatIndustryTempConversionRWH(ConversionTechnology):
    """Lossless downgrade of 0-100 °C heat to recoverable waste heat, the end of the
    temperature cascade."""

    name: str = "heat_industry_temp_conversion_rwh"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Recoverable waste heat."""
        return Attribute(
            "reference_carrier", default_value=["recoverable_waste_heat"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Heat of the 0-100 °C band."""
        return Attribute(
            "input_carrier", default_value=["heat_industry_0_100"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """Recoverable waste heat."""
        return Attribute(
            "output_carrier", default_value=["recoverable_waste_heat"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Lossless."""
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_conversion_factor_temp_conversion(self)

    def _set_lifetime(self) -> Attribute:
        """Assumed lifetime of the temperature cascade."""
        return self.lifetime.set_data(
            default_value=30,
            source=AssumptionInformation(
                description="Assumed lifetime of the temperature cascade."
            ),
        )

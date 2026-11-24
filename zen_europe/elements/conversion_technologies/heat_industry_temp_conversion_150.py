from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_heat_supply import (
    IndustryHeatSupply,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class HeatIndustryTempConversion150(ConversionTechnology):
    """Lossless downgrade of 150-200 °C heat to 100-150 °C."""

    name: str = "heat_industry_temp_conversion_150"
    # bands whose demand flows through the technology
    served_levels: ClassVar[tuple[str, ...]] = ("0_100", "100_150")

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Heat of the 100-150 °C band."""
        return Attribute(
            "reference_carrier", default_value=["heat_industry_100_150"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Heat of the 150-200 °C band."""
        return Attribute(
            "input_carrier", default_value=["heat_industry_150_200"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """Heat of the 100-150 °C band."""
        return Attribute(
            "output_carrier", default_value=["heat_industry_100_150"], element=self
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

    def _set_capacity_existing(self) -> Attribute:
        """Today's heat flow to the lower bands."""
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
        ).get_capacity_existing_temp_conversion(self)

    def _set_capacity_limit(self) -> Attribute:
        """Heat demand of the lower bands times the capacity limit margin."""
        return IndustryHeatSupply(
            self.settings, self.source_path
        ).get_capacity_limit_temp_conversion(self)

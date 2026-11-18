# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_heat_supply import (
    IndustryHeatSupply,
)
from zen_europe.datasets.datasets.technology.industry_general_assumptions import (
    IndustryGeneralAssumptions,
)
from zen_europe.utils.industry import heat_carrier

if TYPE_CHECKING:
    from zen_creator.model import Model


class HeatIndustryTempConversion:
    """Lossless downgrade of a sector's heat to the next lower temperature band."""

    sector: ClassVar[str]
    output_level: ClassVar[str]
    input_level: ClassVar[str]
    # bands whose demand flows through the technology
    served_levels: ClassVar[tuple[str, ...]]

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Heat of the lower band."""
        return Attribute(
            "reference_carrier",
            default_value=[self._heat(self.output_level)],
            element=self,
        )

    def _set_input_carrier(self) -> Attribute:
        """Heat of the higher band."""
        return Attribute(
            "input_carrier", default_value=[self._heat(self.input_level)], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """Heat of the lower band."""
        return Attribute(
            "output_carrier",
            default_value=[self._heat(self.output_level)],
            element=self,
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Lossless."""
        return self.conversion_factor.set_data(
            default_value=[
                {self._heat(self.input_level): {"default_value": 1.0, "unit": "GW/GW"}}
            ],
            source=AssumptionInformation(description="Lossless heat downgrade."),
        )

    def _set_lifetime(self) -> Attribute:
        """Lifetime of the temperature cascade."""
        return IndustryGeneralAssumptions(self.source_path).get_attribute(
            self, "lifetime", "temp_cascade_lifetime"
        )

    def _set_opex_specific_variable(self) -> Attribute:
        """No variable cost."""
        return self.opex_specific_variable.set_data(
            default_value=0.0,
            unit="Euro/GWh",
            source=AssumptionInformation(description="No variable cost."),
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

    def _heat(self, level: str) -> str:
        return heat_carrier(level, self.sector)


class HeatIndustryTempConversion150(HeatIndustryTempConversion):
    output_level: ClassVar[str] = "100_150"
    input_level: ClassVar[str] = "150_200"
    served_levels: ClassVar[tuple[str, ...]] = ("0_100", "100_150")


class HeatIndustryTempConversion100(HeatIndustryTempConversion):
    output_level: ClassVar[str] = "0_100"
    input_level: ClassVar[str] = "100_150"
    served_levels: ClassVar[tuple[str, ...]] = ("0_100",)


class HeatIndustryTempConversion150Glass(
    HeatIndustryTempConversion150, ConversionTechnology
):
    name: str = "heat_industry_temp_conversion_150_glass"
    sector: ClassVar[str] = "glass"


class HeatIndustryTempConversion150Ceramic(
    HeatIndustryTempConversion150, ConversionTechnology
):
    name: str = "heat_industry_temp_conversion_150_ceramic"
    sector: ClassVar[str] = "ceramic"


class HeatIndustryTempConversion150Paper(
    HeatIndustryTempConversion150, ConversionTechnology
):
    name: str = "heat_industry_temp_conversion_150_paper"
    sector: ClassVar[str] = "paper"


class HeatIndustryTempConversion150Food(
    HeatIndustryTempConversion150, ConversionTechnology
):
    name: str = "heat_industry_temp_conversion_150_food"
    sector: ClassVar[str] = "food"


class HeatIndustryTempConversion100Glass(
    HeatIndustryTempConversion100, ConversionTechnology
):
    name: str = "heat_industry_temp_conversion_100_glass"
    sector: ClassVar[str] = "glass"


class HeatIndustryTempConversion100Ceramic(
    HeatIndustryTempConversion100, ConversionTechnology
):
    name: str = "heat_industry_temp_conversion_100_ceramic"
    sector: ClassVar[str] = "ceramic"


class HeatIndustryTempConversion100Paper(
    HeatIndustryTempConversion100, ConversionTechnology
):
    name: str = "heat_industry_temp_conversion_100_paper"
    sector: ClassVar[str] = "paper"


class HeatIndustryTempConversion100Food(
    HeatIndustryTempConversion100, ConversionTechnology
):
    name: str = "heat_industry_temp_conversion_100_food"
    sector: ClassVar[str] = "food"

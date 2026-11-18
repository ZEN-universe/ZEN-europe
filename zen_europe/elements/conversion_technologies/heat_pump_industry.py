# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_heat_supply import (
    IndustryHeatSupply,
)
from zen_europe.datasets.datasets.technology.industry_general_assumptions import (
    IndustryGeneralAssumptions,
)
from zen_europe.elements.conversion_technologies.industry_heat_technology import (
    IndustryHeatTechnology,
)
from zen_europe.utils.industry import heat_carrier


class HeatPumpIndustry(IndustryHeatTechnology):
    """
    Industrial heat pump of a sector and temperature band, on waste heat or water.

    The heat pumps exist for every combination of band, heat source and sector. The
    shared data and assumptions are defined once in this mixin; the concrete
    technologies at the end of the module only set the combination.
    """

    temp_level: ClassVar[str]
    heat_source: ClassVar[str]
    diffusion_proxy: ClassVar[str] = "heat_pump_DH"

    @property
    def cost_proxy(self) -> str:  # type: ignore[override]
        """DEA heat pumps up to 125 °C and 150 °C; the latter also for 150-200 °C."""
        if self.temp_level == "0_100":
            return "heat_pump_industry_125"
        return "heat_pump_industry_150"

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Heat of the sector's temperature band."""
        return Attribute(
            "reference_carrier", default_value=[self._heat()], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """Electricity."""
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """Heat of the sector's temperature band."""
        return Attribute("output_carrier", default_value=[self._heat()], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Fraction of the Carnot COP."""
        assumptions = IndustryGeneralAssumptions(self.source_path)
        return assumptions.get_conversion_factor_heat_pump(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """Investment cost from DEA, plus waste-heat recovery."""
        return self._supply().get_capex_specific_conversion_heat_pump(self)

    def _set_capacity_existing(self) -> Attribute:
        """No industrial heat pumps today."""
        return self.capacity_existing.set_data(
            default_value=0.0,
            unit="GW",
            source=AssumptionInformation(
                description="No existing industrial heat pumps."
            ),
        )

    def _set_capacity_limit(self) -> Attribute:
        """First-year cap; waste heat limit for waste-heat heat pumps."""
        return self._supply().get_capacity_limit_heat_pump(self)

    def _set_capacity_addition_unbounded(self) -> Attribute:
        """Seed from the existing district heating heat pumps."""
        heat_pump_dh = self.model.elements["heat_pump_DH"]
        fleet = float(heat_pump_dh.capacity_existing.df.squeeze().sum())
        return self._supply().get_capacity_addition_unbounded_heat_pump(self, fleet)

    def _heat(self) -> str:
        return heat_carrier(self.temp_level, self.sector)

    def _supply(self) -> IndustryHeatSupply:
        return IndustryHeatSupply(self.settings, self.source_path)


class HeatPumpIndustry0100WasteHeatGlass(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_0_100_waste_heat_glass"
    sector: ClassVar[str] = "glass"
    temp_level: ClassVar[str] = "0_100"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry0100WasteHeatCeramic(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_0_100_waste_heat_ceramic"
    sector: ClassVar[str] = "ceramic"
    temp_level: ClassVar[str] = "0_100"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry0100WasteHeatPaper(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_0_100_waste_heat_paper"
    sector: ClassVar[str] = "paper"
    temp_level: ClassVar[str] = "0_100"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry0100WasteHeatFood(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_0_100_waste_heat_food"
    sector: ClassVar[str] = "food"
    temp_level: ClassVar[str] = "0_100"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry0100WaterGlass(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_0_100_water_glass"
    sector: ClassVar[str] = "glass"
    temp_level: ClassVar[str] = "0_100"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry0100WaterCeramic(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_0_100_water_ceramic"
    sector: ClassVar[str] = "ceramic"
    temp_level: ClassVar[str] = "0_100"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry0100WaterPaper(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_0_100_water_paper"
    sector: ClassVar[str] = "paper"
    temp_level: ClassVar[str] = "0_100"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry0100WaterFood(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_0_100_water_food"
    sector: ClassVar[str] = "food"
    temp_level: ClassVar[str] = "0_100"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry100150WasteHeatGlass(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_100_150_waste_heat_glass"
    sector: ClassVar[str] = "glass"
    temp_level: ClassVar[str] = "100_150"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry100150WasteHeatCeramic(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_100_150_waste_heat_ceramic"
    sector: ClassVar[str] = "ceramic"
    temp_level: ClassVar[str] = "100_150"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry100150WasteHeatPaper(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_100_150_waste_heat_paper"
    sector: ClassVar[str] = "paper"
    temp_level: ClassVar[str] = "100_150"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry100150WasteHeatFood(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_100_150_waste_heat_food"
    sector: ClassVar[str] = "food"
    temp_level: ClassVar[str] = "100_150"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry100150WaterGlass(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_100_150_water_glass"
    sector: ClassVar[str] = "glass"
    temp_level: ClassVar[str] = "100_150"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry100150WaterCeramic(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_100_150_water_ceramic"
    sector: ClassVar[str] = "ceramic"
    temp_level: ClassVar[str] = "100_150"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry100150WaterPaper(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_100_150_water_paper"
    sector: ClassVar[str] = "paper"
    temp_level: ClassVar[str] = "100_150"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry100150WaterFood(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_100_150_water_food"
    sector: ClassVar[str] = "food"
    temp_level: ClassVar[str] = "100_150"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry150200WasteHeatGlass(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_150_200_waste_heat_glass"
    sector: ClassVar[str] = "glass"
    temp_level: ClassVar[str] = "150_200"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry150200WasteHeatCeramic(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_150_200_waste_heat_ceramic"
    sector: ClassVar[str] = "ceramic"
    temp_level: ClassVar[str] = "150_200"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry150200WasteHeatPaper(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_150_200_waste_heat_paper"
    sector: ClassVar[str] = "paper"
    temp_level: ClassVar[str] = "150_200"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry150200WasteHeatFood(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_150_200_waste_heat_food"
    sector: ClassVar[str] = "food"
    temp_level: ClassVar[str] = "150_200"
    heat_source: ClassVar[str] = "waste_heat"


class HeatPumpIndustry150200WaterGlass(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_150_200_water_glass"
    sector: ClassVar[str] = "glass"
    temp_level: ClassVar[str] = "150_200"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry150200WaterCeramic(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_150_200_water_ceramic"
    sector: ClassVar[str] = "ceramic"
    temp_level: ClassVar[str] = "150_200"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry150200WaterPaper(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_150_200_water_paper"
    sector: ClassVar[str] = "paper"
    temp_level: ClassVar[str] = "150_200"
    heat_source: ClassVar[str] = "water"


class HeatPumpIndustry150200WaterFood(HeatPumpIndustry, ConversionTechnology):
    name: str = "heat_pump_industry_150_200_water_food"
    sector: ClassVar[str] = "food"
    temp_level: ClassVar[str] = "150_200"
    heat_source: ClassVar[str] = "water"

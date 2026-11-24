from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.glass_production_data import (
    GlassProductionData,
)
from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class GlassProduction(ConversionTechnology):
    """Production of glass from glass fuel, heat and electricity."""

    name: str = "glass_production"
    sector: ClassVar[str] = "glass"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Glass."""
        return Attribute("reference_carrier", default_value=["glass"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """Glass fuel, electricity and the heat bands below 200 °C. Glass is fired
        with natural gas, the AIDRES (2023) reference route, supplied as glass fuel."""
        return Attribute(
            "input_carrier",
            default_value=[
                "glass_fuel",
                "electricity",
                "heat_industry_0_100",
                "heat_industry_100_150",
                "heat_industry_150_200",
            ],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """Glass."""
        return Attribute("output_carrier", default_value=["glass"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Energy intensity from AIDRES and Rehfeldt (2017)."""
        return GlassProductionData(
            self.settings, self.source_path
        ).get_conversion_factor(self)

    def _set_lifetime(self) -> Attribute:
        """Lifetime from JRC-EU-TIMES."""
        return GlassProductionData(self.settings, self.source_path).get_lifetime(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """No cost: the capacity follows the fixed demand."""
        return self._industry.get_no_cost(self.capex_specific_conversion)

    def _set_opex_specific_fixed(self) -> Attribute:
        """No cost: the capacity follows the fixed demand."""
        return self._industry.get_no_cost(self.opex_specific_fixed)

    def _set_opex_specific_variable(self) -> Attribute:
        """No cost: the production follows the fixed demand."""
        return self._industry.get_no_cost(self.opex_specific_variable)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """Process emissions from AIDRES."""
        return GlassProductionData(
            self.settings, self.source_path
        ).get_carbon_intensity_technology(self)

    def _set_capacity_existing(self) -> Attribute:
        """Production capacity from JRC-IDEES."""
        if not self.settings.investment.use_existing_capacities:
            return self.capacity_existing.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description="We do not consider existing capacities."
                ),
            )
        return GlassProductionData(
            self.settings, self.source_path
        ).get_capacity_existing(self)

    @property
    def _industry(self) -> IndustryProductionData:
        return IndustryProductionData(self.settings, self.source_path)

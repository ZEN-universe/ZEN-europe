from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.ceramic_production_data import (
    CeramicProductionData,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class CeramicProduction(ConversionTechnology):
    """Production of ceramic from fuels, ceramic fuel, heat and electricity."""

    name: str = "ceramic_production"
    sector: ClassVar[str] = "ceramic"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Ceramic."""
        return Attribute("reference_carrier", default_value=["ceramic"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """Fuels, ceramic fuel, heat bands and electricity."""
        return CeramicProductionData(self.settings, self.source_path).get_input_carrier(
            self
        )

    def _set_output_carrier(self) -> Attribute:
        """Ceramic."""
        return Attribute("output_carrier", default_value=["ceramic"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Energy intensity from Rehfeldt (2017)."""
        return CeramicProductionData(
            self.settings, self.source_path
        ).get_conversion_factor(self)

    def _set_lifetime(self) -> Attribute:
        """Lifetime of the cement plant proxy."""
        return CeramicProductionData(self.settings, self.source_path).get_lifetime(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """Investment cost of the cement plant proxy."""
        return CeramicProductionData(
            self.settings, self.source_path
        ).get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """Fixed O&M cost of the cement plant proxy."""
        return CeramicProductionData(
            self.settings, self.source_path
        ).get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """Variable O&M cost of the cement plant proxy."""
        return CeramicProductionData(
            self.settings, self.source_path
        ).get_opex_specific_variable(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """Process emissions from the ceramic BREF."""
        return CeramicProductionData(
            self.settings, self.source_path
        ).get_carbon_intensity_technology(self)

    def _set_capacity_existing(self) -> Attribute:
        """Production capacity: demand per capacity utilisation."""
        if not self.settings.investment.use_existing_capacities:
            return self.capacity_existing.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description="We do not consider existing capacities."
                ),
            )
        return CeramicProductionData(
            self.settings, self.source_path
        ).get_capacity_existing(self)

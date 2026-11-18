# TODO: Jacob decide how to model this. Should be one element per module.
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)
from zen_europe.utils.industry import heat_carrier

if TYPE_CHECKING:
    from zen_creator.model import Model


class IndustryProduction:
    """Production of a sector's product from fuels, heat and electricity."""

    sector: ClassVar[str]

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    def heat_carrier(self, level: str) -> str:
        """The sector's heat carrier of the temperature band `level`."""
        return heat_carrier(level, self.sector)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Product of the sector."""
        return Attribute("reference_carrier", default_value=[self.sector], element=self)

    def _set_input_carrier(self) -> Attribute:
        """Fuels, heat bands and electricity."""
        return self._data().get_input_carrier(self)

    def _set_output_carrier(self) -> Attribute:
        """Product of the sector."""
        return Attribute("output_carrier", default_value=[self.sector], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Energy intensity from Rehfeldt (2017) and AIDRES."""
        return self._data().get_conversion_factor(self)

    def _set_lifetime(self) -> Attribute:
        """Lifetime from JRC-EU-TIMES."""
        return self._data().get_lifetime(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """Investment cost from JRC-EU-TIMES and literature."""
        return self._data().get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """Fixed O&M cost from JRC-EU-TIMES and literature."""
        return self._data().get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """Variable O&M cost from JRC-EU-TIMES and literature."""
        return self._data().get_opex_specific_variable(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """Process emissions."""
        return self._data().get_carbon_intensity_technology(self)

    def _set_capacity_existing(self) -> Attribute:
        """Production capacity from JRC-IDEES and FAOSTAT."""
        if not self.settings.investment.use_existing_capacities:
            return self.capacity_existing.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description="We do not consider existing capacities."
                ),
            )
        return self._data().get_capacity_existing(self)

    def _data(self) -> IndustryProductionData:
        return IndustryProductionData(self.settings, self.source_path)


class GlassProduction(IndustryProduction, ConversionTechnology):
    name: str = "glass_production"
    sector: ClassVar[str] = "glass"


class CeramicProduction(IndustryProduction, ConversionTechnology):
    name: str = "ceramic_production"
    sector: ClassVar[str] = "ceramic"


class PaperProduction(IndustryProduction, ConversionTechnology):
    name: str = "paper_production"
    sector: ClassVar[str] = "paper"


class FoodProduction(IndustryProduction, ConversionTechnology):
    name: str = "food_production"
    sector: ClassVar[str] = "food"

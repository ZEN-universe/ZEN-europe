from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from zen_creator import ConversionTechnology
from zen_creator.datasets.datasets.metadata import AssumptionInformation
from zen_creator.utils.attribute import Attribute

from zen_europe.datasets.dataset_collections.industrial_waste_heat import (
    IndustrialWasteHeat,
)
from zen_europe.datasets.dataset_collections.industry_production_data import (
    IndustryProductionData,
)
from zen_europe.datasets.dataset_collections.paper_production_data import (
    PaperProductionData,
)

if TYPE_CHECKING:
    from zen_creator.model import Model


class PaperProduction(ConversionTechnology):
    """Production of paper from fuels, heat and electricity."""

    name: str = "paper_production"
    sector: ClassVar[str] = "paper"

    def __init__(self, model: Model, power_unit: str = "tproduct/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """Paper."""
        return Attribute("reference_carrier", default_value=["paper"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """Fuels, heat bands and electricity."""
        return PaperProductionData(self.settings, self.source_path).get_input_carrier(
            self
        )

    def _set_output_carrier(self) -> Attribute:
        """Paper and the waste heat of the process."""
        return Attribute(
            "output_carrier",
            default_value=["paper", *self.settings.operation.waste_heat_carriers],
            element=self,
        )

    # ---------- Required methods that are called during object build ----------

    def _set_conversion_factor(self) -> Attribute:
        """Energy intensity from Rehfeldt (2017), plus the waste heat from
        sEEnergies."""
        return IndustrialWasteHeat(
            self.settings, self.source_path
        ).get_conversion_factor_paper_production(self)

    def _set_lifetime(self) -> Attribute:
        """Lifetime from JRC-EU-TIMES."""
        return PaperProductionData(self.settings, self.source_path).get_lifetime(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        """No cost: the capacity follows the fixed demand."""
        return self._industry.get_no_cost(self.capex_specific_conversion)

    def _set_opex_specific_fixed(self) -> Attribute:
        """No cost: the capacity follows the fixed demand."""
        return self._industry.get_no_cost(self.opex_specific_fixed)

    def _set_opex_specific_variable(self) -> Attribute:
        """No cost: the production follows the fixed demand."""
        return self._industry.get_no_cost(self.opex_specific_variable)

    def _set_capacity_existing(self) -> Attribute:
        """Production capacity from JRC-IDEES and the JRC BAT document."""
        if not self.settings.investment.use_existing_capacities:
            return self.capacity_existing.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description="We do not consider existing capacities."
                ),
            )
        return PaperProductionData(
            self.settings, self.source_path
        ).get_capacity_existing(self)

    @property
    def _industry(self) -> IndustryProductionData:
        return IndustryProductionData(self.settings, self.source_path)

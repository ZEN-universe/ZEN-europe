from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import Attribute, ConversionTechnology, SourceInformation


class FischerTropsch(ConversionTechnology):
    """Class containing all data and assumptions for Fischer-Tropsch synthesis
    (hydrogen and carbon to synthetic oil / liquid fuels)."""

    name: str = "fischer_tropsch"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of Fischer-Tropsch synthesis to oil.
        """
        return Attribute(name="reference_carrier", default_value=["oil"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of Fischer-Tropsch synthesis to hydrogen,
        carbon and electricity.
        """
        return Attribute(
            name="input_carrier",
            default_value=["hydrogen", "carbon", "electricity"],
            element=self,
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of Fischer-Tropsch synthesis to oil and
        district heat.
        """
        return Attribute(
            name="output_carrier", default_value=["oil", "district_heat"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of Fischer-Tropsch synthesis.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of Fischer-Tropsch synthesis.

        Values from the DEA technology catalogue for renewable fuels
        (Hydrogen to Jet Fuel), normalized to the oil reference carrier,
        assuming all output is kerosene-equivalent oil.
        https://ens.dk/en/our-services/projections-and-models/technology-data/technology-data-renewable-fuels
        """
        attr = self.conversion_factor

        dea_dataset = DEA(source_path=self.source_path)
        cf = dea_dataset.get_conversion_factor_fischer_tropsch()
        source = SourceInformation(
            description=(
                "The conversion factor of Fischer-Tropsch synthesis is a "
                "manually derived value based on the DEA technology "
                "catalogue for renewable fuels (Hydrogen to Jet Fuel)."
            ),
            metadata=dea_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of Fischer-Tropsch synthesis.

        """
        if self.settings.investment.use_construction_times:
            tech_db = TechnologyCostDatabase(
                settings=self.settings, source_path=self.source_path
            )
            return tech_db.get_construction_time(self)
        else:
            return self.construction_time

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for Fischer-Tropsch
        synthesis.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for
        Fischer-Tropsch synthesis.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for
        Fischer-Tropsch synthesis.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of fischer tropsch.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

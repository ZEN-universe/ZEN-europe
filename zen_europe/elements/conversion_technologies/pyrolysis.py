from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.technology.biochar_market_report import (
    BiocharMarketReport,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator import (
    AssumptionInformation,
    Attribute,
    ConversionTechnology,
    SourceInformation,
)


class Pyrolysis(ConversionTechnology):
    """Class containing all data and assumptions for slow pyrolysis of
    biomass (to hard coal / biochar, oil and district heat)."""

    name: str = "pyrolysis"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of pyrolysis to oil.
        """
        return Attribute(name="reference_carrier", default_value=["oil"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of pyrolysis to biomass and electricity.
        """
        return Attribute(
            name="input_carrier", default_value=["biomass", "electricity"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of pyrolysis to hard coal, district heat and
        oil.
        """
        return Attribute(
            name="output_carrier",
            default_value=["hard_coal", "district_heat", "oil"],
            element=self,
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of pyrolysis.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of pyrolysis.

        """
        attr = self.conversion_factor
        dea_dataset = DEA(source_path=self.source_path)
        cf = dea_dataset.get_conversion_factor_pyrolysis()
        source = SourceInformation(
            description=(
                "The conversion factor of pyrolysis is derived "
                "value based on the DEA technology catalogue for renewable "
                "fuels (Large scale slow pyrolysis, straw feedstock), "
                "normalized to the oil reference carrier."
            ),
            metadata=dea_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of pyrolysis.

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
        Sets the specific capital expenditure (capex) for pyrolysis.

        The technology cost database reports the capex per unit of total
        pyrolysis output, so it is rebased onto the oil reference carrier.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion_pyrolysis(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for
        pyrolysis.

        The technology cost database reports the fixed opex per unit of total
        pyrolysis output, so it is rebased onto the oil reference carrier.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed_pyrolysis(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for
        pyrolysis.

        DEA does not report the specific variable opex for pyrolysis anymore,
        so this method returns a default Attribute object.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        attr = self.opex_specific_variable
        return attr

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of pyrolysis.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            biochar_dataset = BiocharMarketReport(source_path=self.source_path)
            return biochar_dataset.get_capacity_existing(self)
        else:
            attr = self.capacity_existing
            attr.set_data(
                default_value=0,
                df=None,
                source=AssumptionInformation(
                    description=("We do not consider existing capacities."),
                ),
            )
            return attr

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of pyrolysis.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

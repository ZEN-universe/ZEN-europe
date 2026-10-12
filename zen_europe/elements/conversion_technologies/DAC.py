from __future__ import annotations

from typing import TYPE_CHECKING

from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.financial.dea import DEA
from zen_europe.datasets.datasets.technology.DAC_capacities_zurbriggen import (
    DACCapacitiesZurbriggen,
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


class DAC(ConversionTechnology):
    """Class containing all data and assumptions for direct air capture (DAC)."""

    name: str = "DAC"

    def __init__(self, model: Model, power_unit: str = "tCO2/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of DAC to carbon.
        """
        return Attribute(
            name="reference_carrier", default_value=["carbon"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of DAC to electricity and heat.
        """
        return Attribute(
            name="input_carrier", default_value=["electricity", "heat"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of DAC to carbon.
        """
        return Attribute(name="output_carrier", default_value=["carbon"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of DAC.

        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_lifetime(self)

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of DAC.

        """
        attr = self.conversion_factor
        dea_dataset = DEA(source_path=self.source_path)
        cf = dea_dataset.get_conversion_factor_DAC()
        source = SourceInformation(
            description=(
                "The conversion factor of DAC is a manually derived value "
                "based on the DEA technology catalogue for carbon capture, "
                "transport and storage (Solid Adsorption Direct Air Capture "
                "Plant)."
            ),
            metadata=dea_dataset.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of DAC.

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
        Sets the specific capital expenditure (capex) for DAC.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for DAC.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for DAC.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of DAC.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            dac_db = DACCapacitiesZurbriggen(
                settings=self.settings, source_path=self.source_path
            )
            return dac_db.get_capacity_existing(self)
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
        Sets the maximum diffusion rate of DAC.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

    def _set_capacity_addition_unbounded(self) -> Attribute:
        """
        Sets the unbounded capacity addition of carbon storage.

        Returns:
            Attribute: An Attribute object containing the unbounded capacity addition
                data.
        """
        dac_db = DACCapacitiesZurbriggen(
            settings=self.settings, source_path=self.source_path
        )
        data = dac_db.data.copy()
        data = (
            data[["node", "year_construction", "Capacity"]]
            .groupby(["node", "year_construction"])
            .sum()
            .squeeze()
        )
        median_add = data.median()
        n_nodes = len(data.index.get_level_values("node").unique())
        addition = median_add / n_nodes
        attr = self.capacity_addition_unbounded
        return attr.set_data(
            default_value=addition,
            unit="tCO2/h",
            source=SourceInformation(
                description=(
                    "The unbounded capacity addition of carbon storage is "
                    "based on the median planned capacity from the "
                    "Zurbriggen et al. paper, "
                    "divided by the number of nodes in the dataset."
                ),
                metadata=dac_db.metadata,
            ),
        )

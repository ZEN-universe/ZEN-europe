from __future__ import annotations

from typing import TYPE_CHECKING

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

from zen_europe.datasets.dataset_collections.district_heating_data import (
    DistrictHeatingData,
)
from zen_europe.datasets.dataset_collections.heat_demand import HeatDemand
from zen_europe.datasets.datasets.financial.dea import DEA


class DistrictHeatingGrid(ConversionTechnology):
    """Class containing all data and assumptions for district heating grids."""

    name: str = "district_heating_grid"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of district heating grids to heat.
        """
        return Attribute(name="reference_carrier", default_value=["heat"], element=self)

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of district heating grids to district heat.
        """
        return Attribute(
            name="input_carrier", default_value=["district_heat"], element=self
        )

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of district heating grids to heat.
        """
        return Attribute(name="output_carrier", default_value=["heat"], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of district heating grids.

        """
        attr = self.lifetime
        dea = DEA(source_path=self.source_path)
        data = dea.get_dh_distribution_data()
        lifetime = int(data.loc[("suburban", "lifetime", "ref"), "value"].iloc[0])
        source = SourceInformation(
            description=(
                "The lifetime of district heating grids is based on data from the DEA "
                "dataset, which provides information on the distribution of lifetimes "
                "for district heating grids. The specific value used here is the "
                "reference value for suburban district heating grids."
            ),
            metadata=dea.metadata,
        )
        attr.set_data(default_value=lifetime, source=source)
        return attr

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of district heating grids.

        """
        attr = self.conversion_factor
        dea = DEA(source_path=self.source_path)
        cf = dea.get_conversion_factor_district_heating_grid()
        source = SourceInformation(
            description=(
                "The conversion factor of district heating grids is based on data from "
                "the DEA dataset, which provides information on the distribution of "
                "energy losses for district heating grids. The specific value used "
                "here is the reference value for suburban district heating grids."
            ),
            metadata=dea.metadata,
        )
        attr.set_data(default_value=cf, source=source)
        return attr

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of district heating grids.

        """
        if self.settings.investment.use_construction_times:
            attr = self.construction_time
            dea = DEA(source_path=self.source_path)
            data = dea.get_dh_distribution_data()
            construction_time = int(
                data.loc[("suburban", "construction_time", "ref"), "value"].iloc[0]
            )
            source = SourceInformation(
                description=(
                    "The construction time of district heating grids is based on data "
                    "from the DEA dataset, which provides information on the "
                    "construction time for district heating grids. The specific value "
                    "used here is the reference value for suburban district heating "
                    "grids."
                ),
                metadata=dea.metadata,
            )
            attr.set_data(default_value=construction_time, source=source)
            return attr
        else:
            return self.construction_time

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for district heating grids.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        dh_dataset = DistrictHeatingData(
            settings=self.settings, source_path=self.source_path
        )
        capex = dh_dataset.get_capex_specific_conversion(self)
        return capex

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for district heating
        grids.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        dh_dataset = DistrictHeatingData(
            settings=self.settings, source_path=self.source_path
        )
        opex_fixed = dh_dataset.get_opex_specific_fixed(self)
        return opex_fixed

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for district heating
        grids.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        dh_dataset = DistrictHeatingData(
            settings=self.settings, source_path=self.source_path
        )
        opex_variable = dh_dataset.get_opex_specific_variable(self)
        return opex_variable

    def _set_capacity_limit(self) -> Attribute:
        """
        Sets the capacity limit for district heating grids.

        Returns:
            Attribute: An Attribute object containing the capacity limit data.
        """
        dh_dataset = DistrictHeatingData(
            settings=self.settings, source_path=self.source_path
        )
        return dh_dataset.get_capacity_limit(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for district heating grids.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            heat_demand_dataset = HeatDemand(
                settings=self.settings, source_path=self.source_path
            )
            return heat_demand_dataset.get_capacity_existing(self)
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

    def _set_max_load(self) -> Attribute:
        """
        Sets the maximum load for district heating grids.

        Returns:
            Attribute: An Attribute object containing the maximum load data.
        """
        heat_demand_dataset = HeatDemand(
            settings=self.settings, source_path=self.source_path
        )

        return heat_demand_dataset.get_max_load(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of district heating grid.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

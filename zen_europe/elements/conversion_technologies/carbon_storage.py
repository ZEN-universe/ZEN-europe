from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pandas as pd

from zen_europe.datasets.datasets.technology.CO2_storage_costs_ZEP import (
    CO2StorageCostsZEP,
)
from zen_europe.datasets.datasets.technology.energyinst_world_energy_review import (
    EnergyInstituteWorldEnergyReview,
)
from zen_europe.datasets.datasets.technology.IOGP_carbon_storage_projects import (
    IOGPCarbonStorageProjects,
)
from zen_europe.datasets.datasets.technology.northern_lights_costs import (
    NorthernLightsCosts,
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


class CarbonStorage(ConversionTechnology):
    """Class containing all data and assumptions for carbon (CO2) storage."""

    name: str = "carbon_storage"

    def __init__(self, model: Model, power_unit: str = "tCO2/h"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of carbon storage to carbon.
        """
        return Attribute(
            name="reference_carrier", default_value=["carbon"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of carbon storage to carbon.
        """
        return Attribute(name="input_carrier", default_value=["carbon"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of carbon storage to an empty list.

        Carbon storage has no output carrier: captured carbon is permanently
        stored, not converted into another dependent carrier.
        """
        return Attribute(name="output_carrier", default_value=[], element=self)

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of carbon storage.

        """
        zep_costs = CO2StorageCostsZEP(source_path=self.source_path)
        return zep_costs.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of carbon storage.

        """
        if self.settings.investment.use_construction_times:
            nl_costs = NorthernLightsCosts(source_path=self.source_path)
            return nl_costs.get_construction_time(self)
        else:
            return self.construction_time

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of carbon storage.

        Carbon storage has no dependent carrier (input carrier = output carrier
        = carbon), so the conversion factor is left empty.
        """
        attr = self.conversion_factor
        cf: list[dict[str, dict[str, Any]]] = []
        attr.set_data(
            default_value=cf,
            source=AssumptionInformation(
                description=(
                    "The conversion factor of carbon storage is manually set "
                    "to an empty list, as carbon storage has no dependent "
                    "carrier (input carrier = output carrier = carbon)."
                ),
            ),
        )
        return attr

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific conversion capital expenditure (capex) for carbon
        storage.

        Returns:
            Attribute: An Attribute object containing the specific conversion capex
                data.
        """
        nl_costs = NorthernLightsCosts(source_path=self.source_path)

        return nl_costs.get_capex_specific(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for carbon
        storage.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        zep_costs = CO2StorageCostsZEP(source_path=self.source_path)
        return zep_costs.get_opex_specific_variable(self)

    def _set_carbon_intensity_technology(self) -> Attribute:
        """
        Sets the carbon intensity of carbon storage.

        Returns:
            Attribute: An Attribute object containing the carbon intensity data.
        """
        attr = self.carbon_intensity_technology
        attr.set_data(
            default_value=-1,
            unit="ton/tCO2",
            source=AssumptionInformation(
                description=(
                    "The carbon intensity of carbon storage is manually set "
                    "to -1, crediting one unit of permanently stored CO2 per "
                    "unit of carbon processed."
                ),
            ),
        )
        return attr

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of carbon storage.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            igop_projects = IOGPCarbonStorageProjects(
                settings=self.settings, source_path=self.source_path
            )
            return igop_projects.get_capacity_existing(self)
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

    def _set_capacity_limit(self) -> Attribute:
        """
        Sets the capacity limit of carbon storage.

        Returns:
            Attribute: An Attribute object containing the capacity limit data.
        """
        if self.settings.data_source.use_OG_carbon_storage_limit:
            OG_extraction_db = EnergyInstituteWorldEnergyReview(
                source_path=self.source_path
            )
            return OG_extraction_db.get_capacity_limit_carbon_storage(self)
        attr = self.capacity_limit
        data = cast(pd.Series, self.capacity_existing.df).groupby("node").sum()
        data.name = "capacity_limit"
        attr.set_data(
            default_value=0,
            df=data,
            unit="tCO2/h",
            source=SourceInformation(
                description=(
                    "The limit on carbon storage capacity is based on the "
                    "existing capacity from the IOGP report, which includes "
                    "all planned and under construction projects. "
                ),
                metadata=cast(
                    SourceInformation, self.capacity_existing.sources[-1]
                ).metadata,
            ),
        )
        return attr

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of carbon storage.
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
        iogp_projects = IOGPCarbonStorageProjects(
            settings=self.settings, source_path=self.source_path
        )
        data = iogp_projects.get_capacity_existing_data()
        median_add = data.median()
        # n_nodes = len(data.index.get_level_values("node").unique())
        # addition = median_add / n_nodes
        attr = self.capacity_addition_unbounded
        return attr.set_data(
            default_value=median_add,
            unit="tCO2/h",
            source=SourceInformation(
                description=(
                    "The unbounded capacity addition of carbon storage is based on the "
                    "median existing and future capacity from the IOGP report, divided "
                    "by the number of nodes in the dataset."
                ),
                metadata=iogp_projects.metadata,
            ),
        )

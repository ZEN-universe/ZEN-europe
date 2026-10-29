from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pandas as pd

from zen_europe.datasets.dataset_collections.hydro_existing_capacity_plant_level import (  # noqa: E501
    HydroExistingCapacityPlantLevel,
)
from zen_europe.datasets.dataset_collections.hydropower_existing_capacities import (
    HydropowerExistingCapacities,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.technology.storage_technologies_schmidt import (
    StorageTechnologiesSchmidt,
)
from zen_europe.datasets.datasets.technology.technology_diffusion_mannhardt import (
    TechnologyDiffusionMannhardt,
)

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.metadata import (
    AssumptionInformation,
    SourceInformation,
)
from zen_creator.elements import StorageTechnology
from zen_creator.utils.attribute import Attribute


class ReservoirHydro(StorageTechnology):
    """Class containing all data and assumptions for reservoir hydro storage
    technology."""

    name: str = "reservoir_hydro"
    ENTSOE_PSR = "B12"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of reservoir hydro to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Return the lifetime of reservoir hydro.

        """
        storage_technologies = StorageTechnologiesSchmidt(source_path=self.source_path)
        return storage_technologies.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of reservoir hydro.
        """
        if not self.settings.investment.use_construction_times:
            return self.construction_time
        storage_technologies = StorageTechnologiesSchmidt(source_path=self.source_path)
        return storage_technologies.get_construction_time(self)

    def _set_capex_specific_storage(self) -> Attribute:
        """
        Sets the specific capex of the power capacity of reservoir hydro.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_storage(self)

    def _set_capex_specific_storage_energy(self) -> Attribute:
        """
        Sets the specific capex of the energy capacity of reservoir hydro.

        Since reservoir hydro is generally classified as a conversion technology,
        most of the cost data is available for the power capacity,
        but not for the energy capacity. So, we use the energy capacity data of
        pumped hydro as a proxy for reservoir hydro.
        """
        attr = self.capex_specific_storage_energy
        return attr.set_data(
            default_value=0,
            df=None,
            source=AssumptionInformation(
                description=(
                    "The specific capex of the energy capacity of reservoir hydro is "
                    "manually set to 0, since this is a natural storage. "
                    "The costs of the energy capacity are assumed to be included "
                    "in the costs of the power capacity."
                ),
            ),
        )

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed opex of reservoir hydro.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity of reservoir hydro.

        The existing hydro capacities are kept if
        settings.investment.keep_existing_hydro_capacities is set, even if
        existing capacities are otherwise not considered.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if (
            self.settings.investment.use_existing_capacities
            or self.settings.investment.keep_existing_hydro_capacities
        ):
            if self.settings.data_source.use_plant_level_hydro_capacity:
                hydro_dataset = HydroExistingCapacityPlantLevel(
                    source_path=self.source_path,
                )
                attr = hydro_dataset.get_capacity_existing(self)
            else:
                hydro_capacities = HydropowerExistingCapacities(
                    settings=self.settings,
                    source_path=self.source_path,
                )
                attr = hydro_capacities.get_capacity_existing(self)
            return attr
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

    def _set_capacity_existing_energy(self) -> Attribute:
        """
        Sets the existing energy capacity of pumped hydro.

        The existing hydro capacities are kept if
        settings.investment.keep_existing_hydro_capacities is set, even if
        existing capacities are otherwise not considered.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if (
            self.settings.investment.use_existing_capacities
            or self.settings.investment.keep_existing_hydro_capacities
        ):
            if self.settings.data_source.use_plant_level_hydro_capacity:
                hydro_dataset = HydroExistingCapacityPlantLevel(
                    source_path=self.source_path,
                )
                attr = hydro_dataset.get_capacity_existing(self, power=False)
            else:
                hydro_capacities = HydropowerExistingCapacities(
                    settings=self.settings,
                    source_path=self.source_path,
                )
                attr = hydro_capacities.get_capacity_existing_energy(self)
            return attr
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
        Sets the capacity limit for reservoir hydro.

        Returns:
            Attribute: An Attribute object containing the capacity limit data.
        """
        attr = self.capacity_limit
        data = cast(pd.Series, self.capacity_existing.df)
        unit = self.capacity_existing.unit
        capacity_limit = data.groupby(level=0).sum()
        capacity_limit.name = "capacity_limit"
        capacity_limit = capacity_limit.reindex(
            self.model.config.system.set_nodes, fill_value=0
        )
        attr.set_data(
            df=capacity_limit,
            default_value=0,
            source=SourceInformation(
                description=(
                    "The capacity limit is set to the sum of the"
                    "historical capacity additions across all years."
                ),
                metadata=cast(
                    SourceInformation, self.capacity_existing.sources[-1]
                ).metadata,
            ),
            unit=unit,
        )
        return attr

    def _set_capacity_limit_energy(self) -> Attribute:
        """
        Sets the energy capacity limit for reservoir hydro.

        Returns:
            Attribute: An Attribute object containing the capacity limit data.
        """
        attr = self.capacity_limit_energy
        data = cast(pd.Series, self.capacity_existing_energy.df)
        unit = self.capacity_existing_energy.unit
        capacity_limit = data.groupby(level=0).sum()
        capacity_limit.name = "capacity_limit_energy"
        capacity_limit = capacity_limit.reindex(
            self.model.config.system.set_nodes, fill_value=0
        )
        attr.set_data(
            df=capacity_limit,
            default_value=0,
            source=SourceInformation(
                description=(
                    "The energy capacity limit is set to the sum of the"
                    "historical capacity additions across all years."
                ),
                metadata=cast(
                    SourceInformation, self.capacity_existing_energy.sources[-1]
                ).metadata,
            ),
            unit=unit,
        )
        return attr

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of reservoir hydro.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

    def _set_flow_storage_inflow(self) -> Attribute:
        """
        Sets the storage inflow of reservoir hydro.
        """
        hydropower_data = HydropowerExistingCapacities(
            settings=self.settings, source_path=self.source_path
        )
        return hydropower_data.get_flow_storage_inflow(self)

    def _set_efficiency_charge(self) -> Attribute:
        """
        Sets the charging efficiency of reservoir hydro to 0 to avoid charging.
        """
        attr = self.efficiency_charge
        return attr.set_data(
            default_value=0,
            source=AssumptionInformation(
                description=(
                    "The charging efficiency of reservoir hydro is manually set to "
                    "0% to avoid charging, since this is a purely natural storage."
                ),
            ),
        )

    def _set_efficiency_discharge(self) -> Attribute:
        """
        Sets the discharging efficiency of reservoir hydro.
        """
        storage_technologies = StorageTechnologiesSchmidt(source_path=self.source_path)
        return storage_technologies.get_efficiency_discharge(self)

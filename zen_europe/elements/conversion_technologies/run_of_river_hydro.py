from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pandas as pd

from zen_europe.datasets.dataset_collections.hydro_existing_capacity_plant_level import (  # noqa: E501
    HydroExistingCapacityPlantLevel,
)
from zen_europe.datasets.dataset_collections.hydropower_existing_capacities import (
    HydropowerExistingCapacities,
)
from zen_europe.datasets.dataset_collections.lifetime_expectation import (
    LifetimeExpectation,
)
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
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


class RunOfRiverHydro(ConversionTechnology):
    """Class containing all data and assumptions for run-of-river hydro."""

    name: str = "run-of-river_hydro"

    ENTSOE_PSR = "B11"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of run-of-river hydro to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of run-of-river hydro to an empty list.

        This is because run-of-river hydro do not have an input carrier,
        as they convert solar energy directly into electricity.
        """
        return Attribute(name="input_carrier", default_value=[], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of run-of-river hydro to electricity.
        """
        return Attribute(
            name="output_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of run-of-river hydro.

        Per default, we assume a lifetime of 200 years to keep
        the existing capacities in the model. Otherwise, we use the real
        lifetime of the technology.

        """
        if self.settings.investment.use_200y_lifetime_hydro:
            attr = self.lifetime
            return attr.set_data(
                default_value=200,
                source=AssumptionInformation(
                    description=(
                        "The lifetime of run-of-river hydro is set to 200 years, "
                        "as specified in the investment settings."
                    ),
                ),
            )
        else:
            lifetime_expectation = LifetimeExpectation(
                settings=self.settings, source_path=self.source_path
            )
            return lifetime_expectation.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of run-of-river hydro.

        """
        if self.settings.investment.use_construction_times:
            tech_db = TechnologyCostDatabase(
                settings=self.settings, source_path=self.source_path
            )
            return tech_db.get_construction_time(self)
        else:
            return self.construction_time

    def _set_conversion_factor(self) -> Attribute:
        """
        Return the conversion factor of run-of-river hydro.

        The conversion factor is empty, as run-of-river hydro has no input carrier.
        """
        attr = self.conversion_factor
        return attr.set_data(
            default_value=[],
            source=AssumptionInformation(
                description=(
                    "The conversion factor of run-of-river hydro is manually set to an "
                    "empty list, as it has no input carrier."
                ),
            ),
        )

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for run-of-river hydro.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for run-of-river hydro.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for run-of-river
        hydro.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_limit(self) -> Attribute:
        """
        Sets the capacity limit for run-of-river hydro.

        Returns:
            Attribute: An Attribute object containing the capacity limit data.
        """
        attr = self.capacity_limit
        data = cast(pd.Series, self.capacity_existing.df)
        capacity_limit = data.groupby(level=0).sum()
        capacity_limit.name = "capacity_limit"
        capacity_limit.reindex(self.model.config.system.set_nodes, fill_value = 0)
        attr.set_data(
            df=capacity_limit,
            source=SourceInformation(
                description=(
                    "The capacity limit is set to the sum of the"
                    "historical capacity additions across all years."
                ),
                metadata=cast(
                    SourceInformation, self.capacity_existing.sources[-1]
                ).metadata,
            ),
            unit="GW",
        )
        return attr

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for run-of-river hydro.

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
                hydro_capacity = HydroExistingCapacityPlantLevel(
                    source_path=self.source_path,
                )
                attr = hydro_capacity.get_capacity_existing(self)
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

    def _set_max_load(self) -> Attribute:
        """
        Sets the maximum load for run-of-river hydro.

        Returns:
            Attribute: An Attribute object containing the maximum load data.
        """
        hydropower_data = HydropowerExistingCapacities(
            settings=self.settings,
            source_path=self.source_path,
        )
        return hydropower_data.get_max_load_ror_hydro(self)

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of run-of-river hydro.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

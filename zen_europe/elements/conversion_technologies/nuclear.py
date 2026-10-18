from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pandas as pd

from zen_europe.datasets.dataset_collections.lifetime_expectation import (
    LifetimeExpectation,
)
from zen_europe.datasets.dataset_collections.nuclear_max_load import NuclearMaxLoad
from zen_europe.datasets.dataset_collections.technology_cost_database import (
    TechnologyCostDatabase,
)
from zen_europe.datasets.datasets.carrier.eurostat import Eurostat
from zen_europe.datasets.datasets.financial.potencia import Potencia
from zen_europe.datasets.datasets.technology.powerplantmatching import (
    PowerPlantMatching,
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


class Nuclear(ConversionTechnology):
    """Class containing all data and assumptions for nuclear power plants."""

    name: str = "nuclear"

    NUCLEAR_PSR_TYPE = "B14"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    # ---------- Required methods that are called during object construction ----------

    def _set_reference_carrier(self) -> Attribute:
        """
        Sets the reference carrier of nuclear to electricity.
        """
        return Attribute(
            name="reference_carrier", default_value=["electricity"], element=self
        )

    def _set_input_carrier(self) -> Attribute:
        """
        Sets the input carrier of nuclear to natural gas.
        """
        return Attribute(name="input_carrier", default_value=["uranium"], element=self)

    def _set_output_carrier(self) -> Attribute:
        """
        Set the output carrier of nuclear to electricity.
        """
        return Attribute(
            name="output_carrier", default_value=["electricity"], element=self
        )

    # ---------- Required methods that are called during object build ----------

    def _set_lifetime(self) -> Attribute:
        """
        Sets the lifetime of nuclear.

        """
        lifetime_expectation = LifetimeExpectation(
            settings=self.settings, source_path=self.source_path
        )
        return lifetime_expectation.get_lifetime(self)

    def _set_construction_time(self) -> Attribute:
        """
        Sets the construction time of nuclear.

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
        Return the conversion factor of nuclear.

        """
        eurostat_db = Eurostat(settings=self.settings, source_path=self.source_path)
        efficiencies = eurostat_db.get_efficiencies()
        efficiency = efficiencies.get(self.name, None)
        if efficiency is None:
            raise ValueError(
                f"Efficiency for {self.name} is not available in the Eurostat dataset."
            )
        conversion_factor = [
            {
                "uranium": {"default_value": 1 / efficiency, "unit": "GWh/GWh"},
            }
        ]
        attr = self.conversion_factor
        attr.set_data(
            default_value=conversion_factor,
            source=SourceInformation(
                description=(
                    "The conversion factor is derived from the Eurostat dataset as "
                    "the total consumption of uranium divided by "
                    "the total electricity generation from nuclear."
                ),
                metadata=eurostat_db.metadata,
            ),
        )
        return attr

    def _set_capex_specific_conversion(self) -> Attribute:
        """
        Sets the specific capital expenditure (capex) for nuclear.

        Returns:
            Attribute: An Attribute object containing the specific capex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        """
        Sets the specific fixed operational expenditure (opex) for nuclear.

        Returns:
            Attribute: An Attribute object containing the specific fixed opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        """
        Sets the specific variable operational expenditure (opex) for nuclear.

        Returns:
            Attribute: An Attribute object containing the specific variable opex data.
        """
        tech_db = TechnologyCostDatabase(
            settings=self.settings, source_path=self.source_path
        )
        return tech_db.get_opex_specific_variable(self)

    def _set_capacity_existing(self) -> Attribute:
        """
        Sets the existing capacity for nuclear.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        if self.settings.investment.use_existing_capacities:
            powerplantmatching = PowerPlantMatching(source_path=self.source_path)
            return powerplantmatching.get_capacity_existing(self)
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
        Sets the capacity limit for nuclear.

        Returns:
            Attribute: An Attribute object containing the capacity limit data.
        """
        attr = self.capacity_limit
        if self.settings.investment.use_nuclear_phase_out:
            attr.set_data(
                default_value=0,
                source=AssumptionInformation(
                    description=(
                        "The capacity limit is set to 0, "
                        "as the nuclear phase-out is considered."
                    ),
                ),
            )
        elif self.settings.investment.cap_nuclear_capacity_to_past_investments:
            cap_ex = cast(pd.Series, self.capacity_existing.df)
            cap_lim = cap_ex.groupby("node").sum()
            cap_lim.name = "capacity_limit"
            cap_lim.reindex(self.model.config.system.set_nodes, fill_value = 0)
            attr.set_data(
                df=cap_lim,
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

    def _set_max_load(self) -> Attribute:
        """
        Sets the maximum load for nuclear.

        Returns:
            Attribute: An Attribute object containing the maximum load data.
        """
        potencia_db = Potencia(source_path=self.source_path)
        attr = potencia_db.get_max_load(self)
        if self.settings.max_load.use_seasonal_nuclear_max_load:
            nuclear_max_load = NuclearMaxLoad(
                settings=self.settings,
                set_nodes=self.model.config.system.set_nodes,
                source_path=self.source_path,
            )
            nodal_ml_df, total_ml_df = nuclear_max_load.get_max_load(self)
            data: pd.DataFrame | pd.Series
            if self.settings.max_load.use_nodal_nuclear_max_load:
                data = nodal_ml_df
            else:
                data = total_ml_df
                data.name = "max_load"
            data.index.name = "time"
            attr.set_data(
                df=data,
                source=SourceInformation(
                    description=(
                        "The seasonal maximum load for nuclear is derived from the "
                        "ENTSO-E generation and capacity data."
                    ),
                    metadata=nuclear_max_load.metadata,
                ),
                unit="1",
            )
        return attr

    def _set_max_diffusion_rate(self) -> Attribute:
        """
        Sets the maximum diffusion rate of nuclear.
        """
        if not self.settings.investment.use_diffusion_rates:
            return self.max_diffusion_rate
        diffusion_rates = TechnologyDiffusionMannhardt(source_path=self.source_path)
        return diffusion_rates.get_max_diffusion_rate(self)

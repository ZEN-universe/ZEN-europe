from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, cast

import numpy as np
import pandas as pd
from zen_creator import Attribute, DatasetCollection, EnergySystem
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.energy_system.desnz_ghg_inventory import (
    DESNZGreenhouseGasInventory,
)
from zen_europe.datasets.datasets.energy_system.eea_ghg_inventory import (
    EEAGreenhouseGasInventory,
)
from zen_europe.datasets.datasets.energy_system.global_carbon_budget import (
    GlobalCarbonBudget,
)
from zen_europe.datasets.datasets.energy_system.ipcc_ar6 import IPCCAR6
from zen_europe.datasets.datasets.energy_system.worldbank_population import (
    WorldBankPopulation,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset

logger = logging.getLogger(__name__)

# EU emission reduction targets, relative to the 1990 level: Fit for 55
# (Regulation (EU) 2021/1119) for 2030, and Regulation (EU) 2026/667 of the
# European Parliament and of the Council of 11 March 2026 Amending
# Regulation (EU) 2021/1119 as Regards the Setting of a Union Intermediate
# Climate Target for 2040. http://data.europa.eu/eli/reg/2026/667/oj.
EU_1990_REFERENCE_YEAR = 1990
EU_2030_TARGET_YEAR = 2030
EU_2030_TARGET_REDUCTION = 0.55
EU_2040_TARGET_YEAR = 2040
EU_2040_TARGET_REDUCTION = 0.90

# number of most recent years the linear extrapolation is fitted to
EXTRAPOLATION_YEARS = 10


class CarbonConstraints(DatasetCollection):
    """Calculate carbon constraints."""

    name = "carbon_constraints"

    def __init__(self, settings: Settings, source_path: Path | str):
        self.settings = settings
        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "worldbank_population": WorldBankPopulation(source_path=self.source_path),
            "eea_ghg_inventory": EEAGreenhouseGasInventory(
                source_path=self.source_path
            ),
            "ipcc_ar6": IPCCAR6(source_path=self.source_path),
            "desnz_ghg_inventory": DESNZGreenhouseGasInventory(
                source_path=self.source_path
            ),
            "global_carbon_budget": GlobalCarbonBudget(source_path=self.source_path),
        }

    def calculate_carbon_budget(self, energy_system: EnergySystem) -> Attribute:
        """
        Calculate the remaining carbon budget for the energy system.
        """
        global_budget = self.get_remaining_global_carbon_budget()
        share = self.calculate_budget_share_egal(energy_system)
        budget_europe = global_budget * share
        if not self.settings.emissions.correct_budget_with_global_emissions:
            budget_europe = self.correct_budget_with_european_emissions(
                energy_system, budget_europe
            )
        sector_share = self.calculate_sector_share(energy_system)
        year_sector_share = int(
            self.settings.time.reference_year
            if self.settings.time.reference_year in sector_share.index
            else sector_share.index[-1]
        )
        sector_budget = budget_europe * sector_share.loc[year_sector_share]
        attr = energy_system.carbon_emissions_budget
        attr.set_data(
            default_value=sector_budget,
            source=SourceInformation(
                description=(
                    "The remaining carbon budget is calculated based on the "
                    "remaining global carbon budget from the IPCC AR6 report, "
                    "the population share of Europe, and the sectoral emissions "
                    "from the EEA GHG inventory and the DESNZ GHG inventory (UK)."
                ),
                metadata=self.metadata,
            ),
            unit="gigatons",
        )
        return attr

    def calculate_sector_share(self, energy_system: EnergySystem) -> pd.Series:
        """
        Calculate the share of the modeled sectors in the total European
        emissions, by year, based on the EEA GHG inventory and the DESNZ GHG
        inventory (UK).
        """
        sector_emissions = self.calculate_sector_emissions(energy_system)
        total_emissions = self.calculate_total_emissions(energy_system)
        return sector_emissions / total_emissions

    def calculate_sector_emissions(self, energy_system: EnergySystem) -> pd.Series:
        """
        Calculate the CO2 emissions of the modeled sectors, in Gt by year,
        summed over the EEA GHG inventory and the DESNZ GHG inventory (UK).
        """
        eea_ghg_inventory = cast(
            EEAGreenhouseGasInventory, self.data["eea_ghg_inventory"]
        )
        desnz_ghg_inventory = cast(
            DESNZGreenhouseGasInventory, self.data["desnz_ghg_inventory"]
        )
        set_nodes = energy_system.config.system.set_nodes
        sectors = list(energy_system.model.sectors)
        emissions_sectors_EU = eea_ghg_inventory.get_emissions_sectors(
            sectors, set_nodes
        )
        emissions_sectors_UK = desnz_ghg_inventory.get_emissions_sectors(sectors)
        return emissions_sectors_EU.sum() + emissions_sectors_UK.sum()

    def calculate_total_emissions(self, energy_system: EnergySystem) -> pd.Series:
        """
        Calculate the total CO2 emissions of the modeled nodes, in Gt by
        year, summed over the EEA GHG inventory and the DESNZ GHG inventory
        (UK).
        """
        eea_ghg_inventory = cast(
            EEAGreenhouseGasInventory, self.data["eea_ghg_inventory"]
        )
        desnz_ghg_inventory = cast(
            DESNZGreenhouseGasInventory, self.data["desnz_ghg_inventory"]
        )
        set_nodes = energy_system.config.system.set_nodes
        sectors = list(energy_system.model.sectors)
        emissions_total_EU = eea_ghg_inventory.get_emissions_total(set_nodes)
        emissions_total_UK = desnz_ghg_inventory.get_emissions_total(sectors)
        return emissions_total_EU + emissions_total_UK

    def get_remaining_global_carbon_budget(self) -> float:
        """
        Get the remaining carbon budget for a given temperature target and probability.

        The IPCC AR6 budget is counted from the beginning of
        IPCCAR6.AR6_BUDGET_START_YEAR, so the global emissions already emitted
        since then and up to the reference year are deducted from it.
        """
        ipcc_ar6 = cast(IPCCAR6, self.data["ipcc_ar6"])
        temperature_target = self.settings.emissions.temperature_increase
        probability = self.settings.emissions.probability_carbon_budget
        budget_since_ar6_start_year = ipcc_ar6.get_remaining_carbon_budget(
            temperature_target=temperature_target, probability=probability
        )
        if self.settings.emissions.correct_budget_with_global_emissions:
            emitted_since_ar6_start_year = self.get_historic_global_emissions()
            return budget_since_ar6_start_year - emitted_since_ar6_start_year
        else:
            return budget_since_ar6_start_year

    def get_historic_global_emissions(self) -> float:
        """
        Get the global CO2 emissions already emitted between the start of the
        IPCC AR6 carbon budget and the reference year of the model.
        """
        global_carbon_budget = cast(
            GlobalCarbonBudget, self.data["global_carbon_budget"]
        )
        historic_emissions = global_carbon_budget.data
        historic_emissions = self.extrapolate_historic_emissions(
            data=historic_emissions,
            start_year=IPCCAR6.AR6_BUDGET_START_YEAR,
            end_year=self.settings.time.reference_year - 1,
            extrapolate_missing_years=self.settings.emissions.extrapolate_missing_years,
        )
        return historic_emissions.sum()

    def calculate_budget_share_egal(self, energy_system: EnergySystem) -> float:
        """
        Calculate the remaining carbon budget share for each node in the model
        based on the egalitarian principle.
        """
        population = cast(WorldBankPopulation, self.data["worldbank_population"])
        set_nodes = energy_system.config.system.set_nodes
        start_year = self.settings.time.reference_year
        last_year = self.settings.time.last_year
        share = population.get_population_share(set_nodes, start_year, last_year)
        return share

    def calculate_carbon_emissions_annual_limit(
        self, energy_system: EnergySystem
    ) -> Attribute:
        """
        Calculate the annual carbon emissions limit of the modeled sectors.
        """
        trajectory = self.calculate_emissions_trajectory(energy_system)
        attr = energy_system.carbon_emissions_annual_limit
        attr.set_data(
            df=trajectory,
            source=SourceInformation(
                description=(
                    "The annual emissions limit is linearly interpolated "
                    "between the sectoral emissions at the reference year, "
                    "the Fit for 55 target for 2030 and the 2040 target of "
                    "Regulation (EU) 2026/667 (both relative to 1990), and "
                    "net zero in the last year."
                ),
                metadata=self.metadata,
            ),
            unit="gigatons",
        )
        return attr

    def calculate_emissions_trajectory(self, energy_system: EnergySystem) -> pd.Series:
        """
        Calculate the annual carbon emissions limit of the modeled sectors
        for every optimization year, in Gt.

        The trajectory is linearly interpolated between the actual sectoral
        emissions at the year before the reference year, the EU 2030 and
        2040 reduction targets relative to 1990, and net zero in the last
        year.
        """
        sector_emissions = self.calculate_sector_emissions(energy_system)
        emissions_1990 = sector_emissions.loc[EU_1990_REFERENCE_YEAR]
        anchor_year = min(
            self.settings.time.reference_year - 1, max(sector_emissions.index)
        )
        last_year = self.settings.time.last_year
        target_years = pd.Index(
            [anchor_year, EU_2030_TARGET_YEAR, EU_2040_TARGET_YEAR, last_year],
            name="year",
        )
        target_emissions = [
            sector_emissions.loc[anchor_year],
            (1 - EU_2030_TARGET_REDUCTION) * emissions_1990,
            (1 - EU_2040_TARGET_REDUCTION) * emissions_1990,
            0,
        ]
        trajectory = pd.Series(target_emissions, index=target_years)

        optimization_years = pd.Index(self.settings.time.years, name="year")
        trajectory = trajectory.reindex(
            optimization_years.union(target_years)
        ).interpolate(method="index")
        trajectory.name = "carbon_emissions_annual_limit"
        return trajectory.loc[optimization_years]

    def correct_budget_with_european_emissions(
        self, energy_system: EnergySystem, budget_europe: float
    ) -> float:
        """
        Correct the remaining carbon budget of the energy system with the
        actual European emissions between the start of the IPCC AR6 carbon
        budget and the reference year of the model.
        """
        european_emissions = self.calculate_total_emissions(energy_system)
        european_emissions = self.extrapolate_historic_emissions(
            data=european_emissions,
            start_year=IPCCAR6.AR6_BUDGET_START_YEAR,
            end_year=self.settings.time.reference_year - 1,
            extrapolate_missing_years=self.settings.emissions.extrapolate_missing_years,
        )
        remaining_budget = budget_europe - european_emissions.sum()
        return remaining_budget

    def extrapolate_historic_emissions(
        self,
        data: pd.Series,
        start_year: int,
        end_year: int,
        extrapolate_missing_years: bool,
    ) -> pd.Series:
        """
        Check if the historic emissions data contains the requested years,
        and extrapolate missing years if requested.

        Args:
            data (pd.Series): Historic emissions data.
            start_year (int): First year of the period.
            end_year (int): Last year of the period.
            extrapolate_missing_years (bool): If True, years after the last
                reported year are filled with a linear fit of the last
                `EXTRAPOLATION_YEARS` reported years. If False, missing years
                raise an error.
        """
        missing = [year for year in (start_year, end_year) if year not in data.index]
        last_year = int(data.index.max())
        only_after_last_year = all(year > last_year for year in missing)
        if missing and not (extrapolate_missing_years and only_after_last_year):
            raise ValueError(
                f"The Global Carbon Budget does not report the years {missing}. "
                f"Available years: {data.index.min()}-{last_year}."
            )
        if not missing:
            return data.loc[start_year:end_year]

        extrapolated_years = range(last_year + 1, end_year + 1)
        year_str = (
            f"{extrapolated_years[0]}-{end_year}"
            if len(extrapolated_years) > 1
            else str(extrapolated_years[0])
        )
        logger.warning(
            f"Historic emissions are only available until "
            f"{last_year}. Extrapolating values for {year_str} "
            f"linearly from the last {EXTRAPOLATION_YEARS} years."
        )
        reference = data.loc[last_year - EXTRAPOLATION_YEARS + 1 :]
        slope, intercept = np.polyfit(
            reference.index.to_numpy(), reference.to_numpy(dtype=float), deg=1
        )
        extrapolated = pd.Series(
            [slope * year + intercept for year in extrapolated_years],
            index=pd.Index(extrapolated_years, name=data.index.name),
            name=data.name,
        )
        return pd.concat([data, extrapolated]).loc[start_year:end_year]

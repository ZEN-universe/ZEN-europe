from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

from zen_europe.datasets.datasets.technology.glohydrores import GloHydroRes
from zen_europe.datasets.datasets.technology.pecd_hydro_capacities import (
    PECDHydroCapacities,
)

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Technology


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation
from zen_creator.utils.settings import Settings

from zen_europe.datasets.datasets.carrier.entsoe import ENTSOE
from zen_europe.datasets.datasets.technology.jrc_hydro_db import JRCHydroPowerDatabase
from zen_europe.datasets.datasets.technology.powerplantmatching import (
    PowerPlantMatching,
)


class HydroExistingCapacity(DatasetCollection):
    """Extracting existing capacity data for hydro technologies."""

    name = "hydro_existing_capacity"

    def __init__(
        self,
        settings: Settings,
        set_nodes: list[str],
        source_path: Path | None = None,
    ):

        self.settings = settings
        self.set_nodes = set_nodes

        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "jrc_hydro_power_database": JRCHydroPowerDatabase(self.source_path),
            "powerplantmatching": PowerPlantMatching(self.source_path),
            "entsoe": ENTSOE(
                settings=self.settings,
                set_nodes=self.set_nodes,
                source_path=self.source_path,
            ),
            "glohydrores": GloHydroRes(self.source_path),
            "pecd_hydro_capacity": PECDHydroCapacities(self.source_path),
        }

    # TODO deprecated?
    def get_capacity_existing_entsoe_data(self, element: Technology) -> Attribute:
        """
        Get the existing capacity for hydro technologies based on ENTSOE data.

        This function retrieves the existing capacity data for the specified element
        from the ENTSOE dataset.
        Args:
            element (Technology): The element for which to retrieve the existing
                capacity.
        """
        entsoe_dataset = cast(ENTSOE, self.data["entsoe"])
        data_entsoe = entsoe_dataset.get_capacity_existing(
            psr_type=element.ENTSOE_PSR,  # type: ignore[attr-defined]
            year=element.settings.time.year_time_series,
        )
        data_entsoe = data_entsoe.droplevel(1)
        data_entsoe.name = "capacity_existing"

        source = SourceInformation(
            description=(
                "The existing capacity data is derived from the ENTSOE dataset."
            ),
            metadata=self.metadata,
        )
        attr = element.capacity_existing.set_data(
            df=data_entsoe,
            source=source,
            unit="GW",
        )
        return attr

    def get_capacity_existing_pecd_data(
        self, element: Technology, power: bool = True
    ) -> Attribute:
        """
        Get the existing capacity for hydro technologies based on the pecd data.

        This function retrieves the existing capacity data for the specified element
        from the PECD dataset.
        Args:
            element (Technology): The element for which to retrieve the existing
                capacity.
            power (bool): If True, returns the power capacity; if False, returns the
                energy capacity.
        """
        pecd_dataset = cast(PECDHydroCapacities, self.data["pecd_hydro_capacity"])
        return pecd_dataset.get_capacity_existing(element, power=power)

    def get_capacity_existing_plant_level_data(
        self, element: Technology, power: bool = True
    ) -> Attribute:
        """
        Get the existing capacity for hydro technologies based on plant-level data from
        the PowerPlantMatching and GloHydroRes datasets.

        This function retrieves the existing capacity data for the specified element.
        Args:
            element (Technology): The element for which to retrieve the existing
                capacity.
            power (bool): If True, returns the power capacity; if False, returns the
                energy capacity.
        """
        if not power:
            raise NotImplementedError(
                "Extracting energy capacity data is not "
                "implemented for plant-level data."
            )
        ppm_dataset = cast(PowerPlantMatching, self.data["powerplantmatching"])
        glohydrores_dataset = cast(GloHydroRes, self.data["glohydrores"])
        data_ppm = cast(pd.Series, ppm_dataset.get_capacity_existing(element).df)
        data_glohydrores = glohydrores_dataset.get_capacity_existing(element)
        data_combined = pd.concat([data_ppm, data_glohydrores], axis=1).max(axis=1)
        data_combined.index = data_combined.index.set_names(
            ["node", "year_construction"]
        )
        data_combined = data_combined.sort_index()
        data_combined.name = "capacity_existing"

        source = SourceInformation(
            description=(
                "The existing capacity data is derived from the "
                "PowerPlantMatching and GloHydroRes datasets, since they report "
                "construction years."
                " The maximum capacity from both datasets for each year and node "
                "is used to ensure that the most comprehensive data is captured."
            ),
            metadata=self.metadata,
        )
        attr = element.capacity_existing.set_data(
            df=data_combined,
            source=source,
            unit="GW",
        )
        return attr

    # TODO remove this once we have aligned on a datasource
    def plot_capacity_comparison(self, element: Technology):
        """
        Plot a comparison of existing capacity data from different sources.

        Args:
            element (Technology): The element for which to plot the capacity
                comparison.
        """
        jrc_dataset = cast(JRCHydroPowerDatabase, self.data["jrc_hydro_power_database"])
        ppm_dataset = cast(PowerPlantMatching, self.data["powerplantmatching"])
        entsoe_dataset = cast(ENTSOE, self.data["entsoe"])
        glohydrores_dataset = cast(GloHydroRes, self.data["glohydrores"])
        data_jrc = jrc_dataset.get_capacity_existing(element)
        data_ppm = cast(pd.Series, ppm_dataset.get_capacity_existing(element).df)
        total_capacity_ppm = data_ppm.groupby(level=0).sum()
        data_entsoe = entsoe_dataset.get_capacity_existing(
            psr_type=element.ENTSOE_PSR,  # type: ignore[attr-defined]
            year=element.settings.time.year_time_series,
        )
        data_entsoe = data_entsoe.droplevel(1)
        data_glohydrores = glohydrores_dataset.get_capacity_existing(element)
        total_capacity_glohydrores = data_glohydrores.groupby(level=0).sum()
        data_combined = pd.concat([data_ppm, data_glohydrores], axis=1).max(axis=1)
        lifetime = cast(float, element.lifetime.default_value)
        year_retirement = element.settings.time.year_time_series - lifetime
        data_combined_retired = data_combined[
            data_combined.index.get_level_values(1) <= year_retirement
        ]
        total_capacity_combined = data_combined.groupby(level=0).sum()
        total_capacity_combined_retired = data_combined_retired.groupby(level=0).sum()

        total_capacity = pd.concat(
            [
                data_jrc,
                total_capacity_ppm,
                data_entsoe,
                total_capacity_glohydrores,
                total_capacity_combined,
                total_capacity_combined_retired,
            ],
            axis=1,
            keys=[
                "jrc",
                "ppm",
                "entsoe",
                "glohydrores",
                "ppm + glohydrores",
                "ppm + glohydrores (without retired)",
            ],
        )
        total_capacity = total_capacity.loc[element.model.config.system.set_nodes]
        # imported here because matplotlib is slow to import and this is the
        # only use of it
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 6))
        total_capacity.plot.bar(
            stacked=False, title=f"Existing {element.name} Capacity by Source"
        )
        ax.set_ylabel("Capacity (GW)")
        ax.set_xlabel("Country")

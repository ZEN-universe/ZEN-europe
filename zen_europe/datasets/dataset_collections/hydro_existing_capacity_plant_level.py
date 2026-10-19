from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, cast

import pandas as pd

from zen_europe.datasets.datasets.technology.glohydrores import GloHydroRes

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator import Dataset, Technology


from zen_creator import Attribute, DatasetCollection
from zen_creator.utils.attribute import SourceInformation

from zen_europe.datasets.datasets.technology.powerplantmatching import (
    PowerPlantMatching,
)


class HydroExistingCapacityPlantLevel(DatasetCollection):
    """Extracting existing capacity data for hydro technologies."""

    name = "hydro_existing_capacity"

    def __init__(
        self,
        source_path: Path | None = None,
    ):

        super().__init__(source_path=source_path)

    def _get_data(self) -> Dict[str, Dataset[Any]]:
        """Load all available data sources."""

        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset collection.")

        return {
            "powerplantmatching": PowerPlantMatching(self.source_path),
            "glohydrores": GloHydroRes(self.source_path),
        }

    def get_capacity_existing(
        self, element: Technology, power: bool = True
    ) -> Attribute:
        """
        Get the existing capacity for hydro technologies based on plant-level
        data from the PowerPlantMatching and GloHydroRes datasets.

        This function retrieves the existing capacity data for the specified element.
        Args:
            element (Element): The element for which to retrieve the existing capacity.
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
        data_ppm = ppm_dataset.get_capacity_existing(element).df
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

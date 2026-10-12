from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator import Attribute, SourceInformation, StorageTechnology
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.utils import (
    convert_country_names,
    divide_evolution_of_cumulative_capacity,
    format_capacity_existing,
)


class EMMESEnergyStorage(Dataset[pd.DataFrame]):
    """
    European Market Monitor on Energy Storage (EMMES) 9.5 dataset class.

    Provides the cumulative electrochemical storage power capacity per country
    for 2020-2030, extracted from Figure 1 of the report.
    """

    name = "emmes_energy_storage"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "EMMES 9.5 - European Market Monitor on Energy Storage:"
                " Europe's energy storage hits 100 GW"
            ),
            author=["LCP Delta", "Energy Storage Europe Association"],
            publication="Energy Storage Europe Association",
            publication_year=2025,
            note=(
                "The capacity values are read off the stacked bar chart"
                " 'Cumulative power capacity' (Figure 1) of the report."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            Path(self.source_path) / "03-technology" / "capacity_existing" / "battery"
        )

    def _set_data(self) -> pd.DataFrame:
        """
        Cumulative battery power capacity per node and year in GW.
        """
        data = pd.read_csv(self.path / "emmes_battery_power_capacity_by_country_MW.csv")
        data["country"] = convert_country_names(data["country"])
        data = data[data["country"].notna()]
        data = data.set_index("country")
        data.index.name = "node"
        data.columns = data.columns.astype(int)
        return data.fillna(0) / 1000

    # -------- methods ------------------------
    def get_capacity_existing(self, element: StorageTechnology) -> Attribute:
        """
        Get the existing power capacity of a battery storage technology.

        Args:
            element: The element for which to get the existing capacity.

        Returns:
            Attribute: An Attribute object containing the existing capacity data.
        """
        assert element.name == "battery", (
            f"Existing capacity data for {element.name} is not available in the"
            f" {self.name} dataset."
        )
        reference_year = element.settings.time.reference_year
        data = self.data.loc[:, self.data.columns <= reference_year - 1]
        data = divide_evolution_of_cumulative_capacity(data)
        data = format_capacity_existing(data)
        return element.capacity_existing.set_data(
            default_value=0,
            df=data,
            unit="GW",
            source=SourceInformation(
                description=(
                    "The existing power capacity of battery storage is the"
                    " cumulative electrochemical storage capacity per country"
                    " reported in the EMMES 9.5 report, split into capacity"
                    " additions per construction year."
                ),
                metadata=self.metadata,
            ),
        )

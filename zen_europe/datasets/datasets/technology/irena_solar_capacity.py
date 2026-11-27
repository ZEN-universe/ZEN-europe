from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.utils import convert_country_names


class IRENASolarCapacity(Dataset[pd.DataFrame]):
    """
    IRENA solar capacity dataset class.

    The data is the cumulative photovoltaic capacity (GW) per country and year.
    """

    name = "irena_solar_capacity"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Renewable capacity statistics 2026"),
            author=["IRENA"],
            publication="IRENA",
            publication_year=2026,
            url="https://www.irena.org/Publications/2026/Mar/Renewable-capacity-statistics-2026",
            note=(
                "The values from 2006-2025 are from the Renewable Energy Statistics "
                "2016 report"
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return Path(self.source_path) / "03-technology" / "capacity_existing"

    def _set_data(self) -> pd.DataFrame:
        data = pd.read_csv(self.path / "IRENA_solar_pv_capacity_MW_2006-2025.csv")
        data["Country"] = convert_country_names(data["Country"])
        data = data[data["Country"].notna()]
        data = data.set_index("Country")
        data = data.fillna(0)
        data.columns = data.columns.astype(int)
        return data / 1000

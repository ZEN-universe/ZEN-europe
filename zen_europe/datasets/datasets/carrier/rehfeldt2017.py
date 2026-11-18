from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class Rehfeldt2017(Dataset[pd.DataFrame]):
    """Energy intensity and process-heat temperature of industrial sub-processes."""

    name = "rehfeldt2017"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "A bottom-up estimation of the heating and cooling demand in European "
                "industry"
            ),
            author=["Rehfeldt, M.", "Fleiter, T.", "Toro, F."],
            publication="Energy Efficiency",
            publication_year=2017,
            doi="10.1007/s12053-017-9571-y",
            note="Sub-process energy intensities and temperature distributions.",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "industry" / "Rehfeldt2017.csv"

    def _set_data(self) -> pd.DataFrame:
        return pd.read_csv(self.path).set_index(["sector", "sub_process"])

    def get_sub_processes(self, sector: str) -> pd.DataFrame:
        """
        Get the sub-processes of a sector.

        Args:
            sector (str): The industry sector.

        Returns:
            pd.DataFrame: Fuel and electricity intensity (GJ/t), activity (Mt) and
                share of the heat per temperature bin (columns `temp_*`), indexed
                by sub-process.
        """
        return self.data.loc[sector]

    def get_activity_weights(self, sector: str) -> pd.Series:
        """Share of each sub-process in the sector's activity."""
        activity = self.get_sub_processes(sector)["activity_Mt"]
        return activity / activity.sum()

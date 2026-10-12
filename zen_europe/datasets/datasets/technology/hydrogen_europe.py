from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class HydrogenEurope(Dataset[pd.DataFrame]):
    """
    EuroCalliope dataset class for potential capacity.

    """

    name = "hydrogen_rollout_ganter"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Clean Hydrogen Monitor 2024"),
            author=["Hydrogen Europe"],
            publication="Clean Hydrogen Monitor 2024",
            publication_year=2024,
            url="https://hydrogeneurope.eu/wp-content/uploads/2024/11/Clean_Hydrogen_Monitor_11-2024_V2_DIGITAL_draft3-1.pdf",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "capacity_existing" / "electrolysis"

    def _set_data(self) -> pd.DataFrame:
        data = pd.read_excel(
            self.path / "extracted_capacity_additions.xlsx", sheet_name="final"
        )
        return data

    # -------- methods ------------------------
    def get_capacity_existing(self) -> pd.DataFrame:
        """
        Get the existing capacity for electrolysis technologies.

        Returns:
            pd.DataFrame: A single-column DataFrame with the existing capacity data.
        """
        return self.data.set_index(["node", "year_construction"])

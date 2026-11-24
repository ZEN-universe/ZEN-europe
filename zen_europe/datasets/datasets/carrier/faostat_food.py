from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.utils import convert_country_names


class FAOSTATFood(Dataset[pd.DataFrame]):
    """Production of crops and livestock products per country."""

    name = "faostat_food"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="FAOSTAT: Crops and livestock products",
            author=["Food and Agriculture Organization of the United Nations"],
            publication="FAOSTAT",
            publication_year=2026,
            url="https://www.fao.org/faostat/en/#data/QCL",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path
            / "02-carrier"
            / "industry"
            / "FAOSTAT_Production_Crops_Livestock_E_Europe.csv"
        )

    def _set_data(self) -> pd.DataFrame:
        data = pd.read_csv(self.path, encoding="latin1", low_memory=False)
        data = data[data["Element"] == "Production"]
        data["node"] = convert_country_names(data["Area"])
        assert data["node"].notna().all(), "Unknown FAOSTAT area."
        year_columns = [
            c for c in data.columns if c.startswith("Y") and c[1:].isdigit()
        ]
        data = data.set_index(["Item", "node"])[year_columns]
        data.columns = [int(c[1:]) for c in year_columns]
        return data  # t

    def get_production(self, year: int) -> pd.DataFrame:
        """
        Get the production of crops and livestock products.

        Args:
            year (int): The year of the data.

        Returns:
            pd.DataFrame: Production in t, indexed by item, one column per node;
                0 where FAOSTAT reports none.
        """
        return self.data[year].unstack("node").fillna(0.0)

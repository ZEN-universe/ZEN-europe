from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class IndustryProductionCosts(Dataset[pd.DataFrame]):
    """
    Literature costs and lifetimes of industrial production technologies.

    Used where JRC-EU-TIMES has no or no representative process: the paper capex
    and all costs and the lifetime of food production.
    """

    name = "industry_production_costs"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Costs of industrial production technologies, literature review",
            author=["Goericke, H."],
            publication="docs/files/user_guide/industry.md",
            publication_year=2026,
            note="The sources of each value are given in the description column.",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path
            / "03-technology"
            / "industry"
            / "industry_production_costs.csv"
        )

    def _set_data(self) -> pd.DataFrame:
        return pd.read_csv(self.path).set_index(["sector", "parameter"])

    def get_value(self, sector: str, parameter: str) -> float:
        """Value of a cost (Euro/(t/a) or Euro/t) or the lifetime (yr)."""
        return float(self.data.at[(sector, parameter), "value"])

    def get_price_year(self, sector: str, parameter: str) -> int | None:
        """Price year of a cost, None if the value is not inflated."""
        price_year = self.data.at[(sector, parameter), "price_year"]
        return None if pd.isna(price_year) else int(price_year)

    def get_description(self, sector: str, parameter: str) -> str:
        """Sources and assumptions of a value."""
        return str(self.data.at[(sector, parameter), "description"])

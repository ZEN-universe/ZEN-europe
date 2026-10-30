from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import convert_country_names

class HydrogenMarketLandscapeObservatory(Dataset[pd.Series]):
    """
    Dataset class for the utilization factor of SMR technologies
    based on the European hydrogen market landscape 2025 report.

    """

    name = "hydrogen_market_landscape_observatory"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "The European hydrogen market landscape - November 2025"
            ),
            author=["European Hydrogen Observatory"],
            publication="European Hydrogen Observatory",
            publication_year=2025,
            url="https://observatory.clean-hydrogen.europa.eu/tools-reports/observatory-reports",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path

    def _set_data(self) -> pd.Series:
        """
        No data to be set.
        """
        data: dict[str, float] = {}
        return pd.Series(data)

    # -------- methods ------------------------
    def get_utilization_rate_SMR(self) -> list[dict[str, dict[str, Any]]]:
        """Get the utilization rate for SMR technologies in 2024.

        The data is obtained from the p.5 of the report.

        Returns:
            The utilization rate.
        """
        utilization_rate = 0.7
        return utilization_rate

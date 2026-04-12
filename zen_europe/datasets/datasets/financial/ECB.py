from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
import scipy.stats as stats
from zen_creator.datasets.datasets.dataset import Dataset


class ECB(Dataset[pd.DataFrame]):
    """Dataset class for ECB data."""

    name = "ecb"

    def __init__(self):
        super().__init__(source_path=None)

    # ------ Metadata properties ------
    def _set_author(self) -> str:
        return "European Central Bank"

    def _set_publication_year(self) -> int:
        return 2025

    def _set_url(self) -> str:
        return "https://data.ecb.europa.eu/"

    def _set_path(self) -> Path | None:
        return None  # ECB data is accessed directly via URL, no local path needed

    # ----- Property overwrites -----

    # ----- Load and format Data -----

    def _set_data(self) -> pd.DataFrame:
        """Method to get the inflation rate from ECB data."""
        url = "https://data-api.ecb.europa.eu/service/data/ICP/M.U2.N.000000.4.ANR?format=csvdata"
        df = pd.read_csv(url)
        df_sel = (
            df[["TIME_PERIOD", "OBS_VALUE"]]
            .set_index("TIME_PERIOD")
            .astype(float)
            .squeeze()
        )
        df_sel.index = pd.MultiIndex.from_tuples(
            df_sel.index.map(lambda x: (int(x.split("-")[0]), int(x.split("-")[1]))),
            names=["year", "month"],
        )
        inflation_data = (df_sel / 100 + 1).groupby(level="year").apply(stats.gmean)
        return inflation_data.to_frame(name="inflation_rate")

    # ------ Outward facing functions ------

    def get_inflation_rate(self, base_year: int, target_year: int) -> float:
        """Method to calculate the inflation rate between two years."""
        inflation_rate = self.data.loc[base_year : target_year - 1, "inflation_rate"]
        inflation = float(inflation_rate.prod())
        return inflation

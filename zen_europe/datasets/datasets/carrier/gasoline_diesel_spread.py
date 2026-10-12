from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class GasolineDieselSpread(Dataset[pd.DataFrame]):
    """
    Assumption regarding the gasoline-diesel spread compared to the crude oil price.

    """

    name = "gasoline_diesel_spread"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("Is the refining margin stationary?"),
            author=["Javier Población", "Gregorio Serna"],
            publication="International Review of Economics & Finance",
            publication_year=2016,
            url="https://www.sciencedirect.com/science/article/pii/S1059056016300247",
            doi="http://dx.doi.org/10.1016/j.iref.2016.04.011",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.Series:
        return pd.Series()

    # -------- methods ------------------------
    def get_crack_spread(self) -> int:
        """sets the manual data for the gasoline-diesel spread.

        We assume that the relative gasoline-diesel spread is stationary and
        does not depend on the crude oil price. Their absolute crack spread is
        roughly 15 $/bbl, at a crude oil price of around 70 $/bbl
        (https://www.macrotrends.net/1369/crude-oil-price-history-chart)

        """
        return 15 / 70

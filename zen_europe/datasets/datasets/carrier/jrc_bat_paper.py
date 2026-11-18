from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.industry import NODES_WITHOUT_IDEES
from zen_europe.utils.utils import convert_country_names


class JRCBATPaper(Dataset[pd.DataFrame]):
    """Paper consumption of the countries not covered by JRC-IDEES."""

    name = "jrc_bat_paper"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Best Available Techniques (BAT) reference document for the production "
                "of pulp, paper and board"
            ),
            author=["European Commission, Joint Research Centre"],
            publication="Publications Office of the European Union",
            publication_year=2015,
            doi="10.2791/370629",
            note="Tables 1.1-1.2, paper consumption 2008.",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path
            / "02-carrier"
            / "industry"
            / "JRC_BAT_Paper2014_Table1_2.csv"
        )

    def _set_data(self) -> pd.DataFrame:
        data = pd.read_csv(self.path)
        data["node"] = convert_country_names(data["country"])
        return data.dropna(subset="node").set_index("node")

    def get_consumption(self) -> pd.Series:
        """Paper consumption (kt/a) in 2008 of CH, NO and UK."""
        return self.data.loc[
            list(NODES_WITHOUT_IDEES), "consumption_1000t_2008"
        ].astype(float)

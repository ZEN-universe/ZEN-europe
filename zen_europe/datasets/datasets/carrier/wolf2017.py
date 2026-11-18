from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

# Wolf (2017) industry branch of each industry heat sector
SECTOR_TO_BRANCH = {
    "food": "Nahrung",
    "paper": "Papier",
    "glass": "Nichtmetall",
    "ceramic": "Nichtmetall",
}


class Wolf2017(Dataset[pd.DataFrame]):
    """Process heat demand of German industry branches by temperature level."""

    name = "wolf2017"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Integration von Wärmepumpen in industrielle Produktionssysteme - "
                "Potenziale und Instrumente zur Potenzialerschließung"
            ),
            author=["Wolf, S."],
            publication="PhD thesis, University of Stuttgart",
            publication_year=2017,
            note="Table 4-7, process heat up to 150 °C and up to 200 °C.",
        )

    def _set_path(self) -> Path:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "industry" / "Wolf2017_Tabelle4_7.csv"

    def _set_data(self) -> pd.DataFrame:
        return pd.read_csv(self.path).set_index("industriezweig")

    def get_temperature_split(self) -> pd.DataFrame:
        """
        Get the split of the 100-200 °C process heat into the 100-150 °C and
        150-200 °C bands.

        Returns:
            pd.DataFrame: Shares of the bands "100_150" and "150_200", indexed by
                industry heat sector.
        """
        heat = self.data.loc[
            list(SECTOR_TO_BRANCH.values()), ["PW_bis_150C", "PW_bis_200C"]
        ]
        # shares are given as strings, e.g. "13%"
        heat = heat.apply(lambda column: column.str.strip("%").astype(float) / 100)
        heat.index = list(SECTOR_TO_BRANCH)
        heat.columns = ["100_150", "150_200"]
        return heat.div(heat.sum(axis=1), axis=0)

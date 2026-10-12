from __future__ import annotations

from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class HRE(Dataset[pd.DataFrame]):
    """
    Heat Roadmap Europe (HRE) 5 dataset.

    """

    name = "hre"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("HRE5: Heat Roadmap Europe 5"),
            author=[
                "Brian Vad Mathiesen",
                "Enric Gonzalez Gonzalo",
                "Marina Georgati",
                "Steffen Nielsen",
                "Jelena Nikolic",
                "Alisson Aparecido Vitoriano Julio",
                "Nikolaj Lottrup Bruun-Nielsen",
            ],
            publication="Aalborg Universitet",
            publication_year=2025,
            url="https://vbn.aau.dk/en/projects/hre5-heat-roadmap-europe-5/",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            Path(self.source_path)
            / "03-technology"
            / "district_heating"
            / "HRE_5_DH_potential.csv"
        )

    def _set_data(self) -> pd.Series:
        data = pd.read_csv(self.path).set_index("node")
        return data

    # -------- methods ------------------------
    def get_district_heating_potential(self) -> pd.Series:
        """
        Get the district heating potential from the HRE5 dataset.

        Returns:
            pd.Series: District heating potential indexed by node.

        """
        return self.data

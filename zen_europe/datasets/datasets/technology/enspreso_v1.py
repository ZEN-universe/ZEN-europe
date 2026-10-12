from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class ENSPRESOV1(Dataset[dict[str, pd.Series]]):
    """
    ENSPRESO v1 dataset class for potential capacity.

    """

    name = "enspreso_v1"

    COLUMN_MAPPING = {
        "wind_onshore": "wind_onshore_capacity_gw_high",
        "photovoltaics": "solar_capacity_gw_high_pv_ground",
        "wind_offshore": "wind_offshore_capacity_gw_high_total",
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "ENSPRESO - an open, EU-28 wide, transparent and coherent database of "
                "wind, solar and biomass energy potentials"
            ),
            author=[
                "P. Ruiz",
                "W. Nijs",
                "D. Tarvydas",
                "A. Sgobbi",
                "A. Zucker",
                "R. Pilli",
                "R. Jonsson",
                "A. Camia",
                "C. Thiel",
                "C. Hoyer-Klick",
                "F. Dalla Longa",
                "T. Kober",
                "J. Badger",
                "P. Volker",
                "B.S. Elbersen",
                "A. Brosowski",
                "D. Thrän",
            ],
            publication="Energy Strategy Reviews",
            publication_year=2019,
            url="https://www.sciencedirect.com/science/article/pii/S2211467X19300720",
            doi="https://doi.org/10.1016/j.esr.2019.100379",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            Path(self.source_path) / "03-technology" / "potential_capacity_renewables"
        )

    def _set_data(self) -> dict[str, pd.Series]:
        data = {}
        # onshore and pv
        data_pv_wind_onshore = pd.read_csv(
            self.path / "ENSPRESO_Integrated_NUTS2_Data.csv", delimiter=";"
        )
        data_pv_wind_onshore["nuts0_code"] = data_pv_wind_onshore["nuts2_code"].apply(
            lambda code: code[0:2]
        )
        data_pv_wind_onshore = data_pv_wind_onshore.groupby("nuts0_code").sum(
            numeric_only=True
        )
        data_pv_wind_onshore = data_pv_wind_onshore
        data["wind_onshore"] = data_pv_wind_onshore[self.COLUMN_MAPPING["wind_onshore"]]
        data["photovoltaics"] = data_pv_wind_onshore[
            self.COLUMN_MAPPING["photovoltaics"]
        ]
        # offshore
        data_wind_offshore = pd.read_csv(
            self.path / "ENSPRESO_Integrated_EEZ_Data_Offshore.csv", delimiter=";"
        )
        data_wind_offshore["nuts0_code"] = data_wind_offshore["eez_code_2016"].apply(
            lambda code: code[2:]
        )
        data_wind_offshore = data_wind_offshore.groupby("nuts0_code").sum(
            numeric_only=True
        )
        data_wind_offshore = data_wind_offshore
        data["wind_offshore"] = data_wind_offshore[self.COLUMN_MAPPING["wind_offshore"]]
        return data

    # -------- methods ------------------------
    def get_capacity_limit(self, element) -> pd.Series:
        """
        Get the potential capacity for renewable technologies.

        Args:
            element: The element for which to get the potential capacity.

        Returns:
            pd.Series: A pandas Series containing the potential capacity data.
        """
        if element.name not in self.COLUMN_MAPPING:
            raise ValueError(
                f"Potential capacity data for {element.name} is not available in the "
                "ENSPRESO v1 dataset."
            )
        if element.name == "wind_onshore":
            logging.info(
                "ENSPRESO v2 is released for onshore wind. Check and maybe update the "
                "dataset."
            )
        return self.data[element.name]

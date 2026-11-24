from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class SSBRoadTraffic(Dataset[pd.Series]):
    """
    SSB road traffic volumes dataset class.

    StatBank table 12575 of Statistics Norway, road traffic volumes of all
    passenger cars registered in Norway, queried from the SSB API as csv.
    """

    name = "ssb_road_traffic"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Road traffic volumes, by type of vehicle (table 12575)",
            author=["Statistics Norway (SSB)"],
            publication="SSB",
            publication_year=2026,
            url="https://www.ssb.no/en/statbank/table/12575",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path
            / "02-carrier"
            / "transport"
            / "ssb"
            / "12575_passenger_cars.csv"
        )

    def _set_data(self) -> pd.Series:
        """Road traffic volumes (million km) of passenger cars per year."""
        data = pd.read_csv(self.path, index_col="year")
        return data.iloc[:, -1].astype(float)

    # -------- methods ------------------------
    def get_passenger_car_vehicle_km(self, year: int) -> float:
        """
        Get the vehicle-km (million km) driven by passenger cars in Norway.

        Args:
            year (int): The year of the data.
        """
        return float(self.data[year])

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.utils.constants import Constants


class DfTRoadTraffic(Dataset[pd.DataFrame]):
    """
    DfT road traffic statistics dataset class.

    Table TRA0101 (vehicle miles by vehicle type in Great Britain), converted from
    the published ODS file to csv without changing the values.
    """

    name = "dft_road_traffic"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "TRA0101: Road traffic (vehicle miles) by vehicle type in Great "
                "Britain, annual from 1949"
            ),
            author=["Department for Transport (DfT)"],
            publication="DfT",
            publication_year=2026,
            url="https://www.gov.uk/government/statistical-data-sets/road-traffic-statistics-tra",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "02-carrier" / "transport" / "dft" / "tra0101.csv"

    def _set_data(self) -> pd.DataFrame:
        return pd.read_csv(self.path, index_col="Year")

    # -------- methods ------------------------
    def get_passenger_car_vehicle_km(self, year: int) -> float:
        """
        Get the vehicle-km (million km) driven by cars and taxis in Great Britain.

        Args:
            year (int): The year of the data.
        """
        billion_miles = float(self.data.loc[year, "Cars and Taxis"])
        return billion_miles * Constants.KM_PER_MILE * 1000

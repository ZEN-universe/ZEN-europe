from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData


class BFSPassengerTransport(Dataset[pd.Series]):
    """
    BFS passenger transport dataset class.

    Table T 11.4.1.1 (Fahrleistungen und Fahrzeugbewegungen im Personenverkehr) of
    the Swiss Federal Statistical Office, covering traffic on Swiss territory.
    """

    name = "bfs_passenger_transport"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Fahrleistungen und Fahrzeugbewegungen im Personenverkehr",
            author=["Bundesamt für Statistik (BFS)"],
            publication="BFS",
            publication_year=2026,
            url="https://statistik.admin.ch/de/asset/36851390",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            self.source_path
            / "02-carrier"
            / "transport"
            / "bfs"
            / "fahrleistungen_personenverkehr.xlsx"
        )

    def _set_data(self) -> pd.Series:
        """Vehicle-km (million km) of passenger cars per year."""
        sheet = pd.read_excel(self.path, sheet_name="2005-2025", header=None)
        # the year columns alternate with columns of footnote markers
        years = pd.to_numeric(sheet.iloc[1], errors="coerce").dropna().astype(int)
        cars = sheet[sheet[0].astype(str).str.strip() == "Personenwagen"].iloc[0]
        return pd.Series(cars[years.index].astype(float).values, index=years.values)

    # -------- methods ------------------------
    def get_passenger_car_vehicle_km(self, year: int) -> float:
        """
        Get the vehicle-km (million km) driven by passenger cars in Switzerland.

        Args:
            year (int): The year of the data.
        """
        return float(self.data[year])

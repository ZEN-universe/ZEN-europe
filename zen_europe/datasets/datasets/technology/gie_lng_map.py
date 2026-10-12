from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.elements import Element

from zen_europe.utils.constants import Constants


class GIELNGMap(Dataset[pd.DataFrame]):
    """
    GIE LNG Map dataset class for LNG.

    This class implements the specific behavior for the GIE LNG Map dataset.

    We extract the data from the GIE LNG Map dataset, which provides information on
    existing LNG terminals and their capacities. The dataset is loaded from a CSV file
    and processed to calculate the existing capacity of LNG terminals.

    Some terminals report their maximum send-out capacity in m3/h,
    while others report their annual capacity in bcm/year.
    We convert both to GWh and take the maximum of the two as the existing capacity.
    """

    name = "gie_lng_map"

    _GCV_LNG = (
        Constants.LNG_GCV_KWH_PER_M3
    )  # most common value in the scigrid database, in kWh/m3

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=("GIE LNG Map"),
            author=["Gas Infrastructure Europe (GIE)"],
            publication="GIE",
            publication_year=2024,
            url="https://www.gie.eu/publications/maps/gie-lng-map/",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return self.source_path / "03-technology" / "lng"

    def _set_data(self) -> pd.DataFrame:
        lng_terminals_raw = pd.read_csv(
            self.path / "lng_capacity_existing.csv", delimiter=";"
        )
        lng_terminals_raw = lng_terminals_raw.set_index(["node", "year_construction"])
        lng_terminals_raw["GWh_annual"] = (
            lng_terminals_raw["capacity_bcm_per_year"] * self._GCV_LNG * 1000
        )
        lng_terminals_raw["GWh_hourly"] = (
            lng_terminals_raw["send_out_cm_per_h"] * self._GCV_LNG / 1e6
        )
        lng_terminals_raw["capacity_existing"] = pd.concat(
            [
                lng_terminals_raw["GWh_hourly"].fillna(0),
                lng_terminals_raw["GWh_annual"] / Constants.HOURS_PER_YEAR,
            ],
            axis=1,
        ).max(axis=1)
        lng_terminals = lng_terminals_raw["capacity_existing"]
        return lng_terminals

    def _calculate_capacity_existing_lng(self, element: Element) -> pd.Series:
        """
        Calculate the existing capacity of LNG terminals for a given element.

        Args:
            element (Element): The element for which to calculate the existing capacity.

        Returns:
            pd.Series: A pandas Series containing the existing capacity of LNG terminals
                for the specified element.
        """
        capacity_existing = self.data
        return capacity_existing

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import geopandas as gpd
import pandas as pd
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings

if TYPE_CHECKING:
    from zen_creator import Technology


class ENSPRESO2(Dataset[dict[str, pd.Series]]):
    """
    ENSPRESO 2 onshore and offshore wind potential per country (GW).

    The JRC publishes onshore and offshore as two datasets with their own files;
    only the attribute tables are read.
    - Onshore: NUTS0 totals of the high scenario (500 m setback from settlements,
      sites with a capacity factor of at least 20%, `high_MW`). It is the same
      for all countries; the reference scenario mixes national setback rules.
      ENSPRESO 2 does not cover the UK.
    - Offshore: fixed-bottom potential per exclusive economic zone at sites with a
      capacity factor of at least 30% in the reference scenario (`FX_RF_MWCF`).
    """

    name = "enspreso2"

    # technology: (url, file name, NUTS0 column, capacity column in MW)
    FILES = {
        "wind_onshore": (
            "https://research-data.ec.europa.eu/api/records/yyee7-q1b02/files/"
            "wind_onshore_NUTS.gpkg/content",
            "enspreso2_onshore_wind_nuts.gpkg",
            "NUTS_ID",
            "high_MW",
        ),
        "wind_offshore": (
            "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/ENSPRESO/OFFSHORE-WIND/"
            "eez_data/enspreso2_offshore_wind_eez_data.dbf",
            "enspreso2_offshore_wind_eez_data.dbf",
            "NUTS0",
            "FX_RF_MWCF",
        ),
    }

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "ENSPRESO 2 - The onshore and offshore wind potential of the EU and "
                "neighbouring countries"
            ),
            author=["P. Elsner", "J. Collaer", "A. Uihlein"],
            publication="JRC Data Catalogue",
            publication_year=2025,
            url="https://data.jrc.ec.europa.eu/dataset/542eabfb-377f-4bb7-ab24-8d5e60c30caa",
            doi="https://doi.org/10.2905/JRC.4031F30",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            Path(self.source_path) / "03-technology" / "potential_capacity_renewables"
        )

    def _set_data(self) -> dict[str, pd.Series]:
        data = {}
        for technology, (url, file_name, node_column, column) in self.FILES.items():
            file_path = self.path / file_name
            if (
                get_active_cache_settings().overwrite_enspreso2
                or not file_path.exists()
            ):
                logging.info(f"Downloading {self.name} {technology} from {url}...")
                request = urllib.request.Request(
                    url, headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(request) as response:
                    file_path.write_bytes(response.read())
            table = gpd.read_file(file_path, ignore_geometry=True)
            if "LEVL_CODE" in table:
                table = table[table["LEVL_CODE"] == 0]
            table = table.dropna(subset=[node_column]).set_index(node_column)
            data[technology] = table[column] / 1000  # MW -> GW
        return data

    # -------- methods ------------------------
    def get_capacity_limit(self, element: Technology) -> pd.Series:
        """
        Get the onshore or fixed-bottom offshore wind potential in GW per node.

        Args:
            element: The element for which to get the potential capacity.

        Returns:
            pd.Series: The potential capacity per node in GW.
        """
        if element.name not in self.data:
            raise ValueError(
                f"Potential capacity data for {element.name} is not available in the "
                "ENSPRESO 2 dataset."
            )
        return self.data[element.name].copy()

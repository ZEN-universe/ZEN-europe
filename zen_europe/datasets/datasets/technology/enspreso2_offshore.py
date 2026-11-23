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


class ENSPRESO2Offshore(Dataset[pd.Series]):
    """
    ENSPRESO 2 offshore wind potential per exclusive economic zone (EEZ).

    The JRC publishes the potential as the attribute table of a shapefile; only the
    table (.dbf) is downloaded. We use the fixed-bottom capacity at sites with a
    capacity factor of at least 30% in the reference scenario (`FX_RF_MWCF`, MW).
    Floating potentials (`FL_*`) and the high scenario (`*_HG_*`) are not used.
    Unlike ENSPRESO v1, the EEZ data covers neighbouring countries such as Norway.
    """

    name = "enspreso2_offshore"

    URL = (
        "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/ENSPRESO/OFFSHORE-WIND/"
        "eez_data/enspreso2_offshore_wind_eez_data.dbf"
    )
    FILE_NAME = "enspreso2_offshore_wind_eez_data.dbf"
    COLUMN = "FX_RF_MWCF"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="ENSPRESO 2 - Offshore wind potential per exclusive economic zone",
            author=["European Commission, Joint Research Centre (JRC)"],
            publication="JRC Data Catalogue",
            publication_year=2025,
            url="https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/ENSPRESO/OFFSHORE-WIND/",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            raise ValueError("source_path must be set to load the dataset.")
        return (
            Path(self.source_path) / "03-technology" / "potential_capacity_renewables"
        )

    def _set_data(self) -> pd.Series:
        file_path = self.path / self.FILE_NAME
        if get_active_cache_settings().overwrite_enspreso2_offshore or not (
            file_path.exists()
        ):
            logging.info(f"Downloading {self.name} from {self.URL}...")
            request = urllib.request.Request(
                self.URL, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(request) as response:
                file_path.write_bytes(response.read())
        data = gpd.read_file(file_path, ignore_geometry=True)
        data = data.dropna(subset=["NUTS0"]).set_index("NUTS0")
        return data[self.COLUMN] / 1000  # MW -> GW

    # -------- methods ------------------------
    def get_capacity_limit(self, element: Technology) -> pd.Series:
        """
        Get the fixed-bottom offshore wind potential in GW per node.

        Args:
            element: The element for which to get the potential capacity.

        Returns:
            pd.Series: The potential capacity per node in GW.
        """
        if element.name != "wind_offshore":
            raise ValueError(
                f"Potential capacity data for {element.name} is not available in the "
                "ENSPRESO 2 offshore dataset."
            )
        return self.data.copy()

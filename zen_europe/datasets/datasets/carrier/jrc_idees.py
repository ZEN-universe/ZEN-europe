from __future__ import annotations

import logging
import zipfile
from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from zen_creator.elements.element import Element
import pandas as pd
import requests
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings
from zen_europe.utils.constants import Constants

logger = logging.getLogger(__name__)

# JRC-IDEES only covers the EU27; countries are identified by the same
# ISO 3166-1 alpha-2 codes used as node names elsewhere in zen_europe.
_JRC_IDEES_BASE_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/JRC-IDEES/JRC-IDEES-2023_v1/"
)
_JRC_IDEES_COUNTRIES = [
    "AT",
    "BE",
    "BG",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "EL",
    "ES",
    "FI",
    "FR",
    "HR",
    "HU",
    "IE",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
    "SK",
]
# rows in the *_hh_tes sheets are already pre-aggregated across energy
# carriers (i.e. "Space heating" is the sum of the fuel-specific rows below
# it); the tertiary sheet labels water heating "Hot water" instead of
# "Water heating".
_JRC_IDEES_TES_ROWS = {
    "Space heating": "space_heating",
    "Water heating": "water_heating",
    "Hot water": "water_heating",
}
_KTOE2GWH = 1 / Constants.TOE_PER_MWH  # ktoe (useful energy) -> GWh


class JRCIDEES(Dataset[pd.DataFrame]):
    """
    JRC-IDEES dataset class.

    This class implements the specific behavior for the JRC-IDEES dataset.
    """

    name = "jrc_idees"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "JRC-IDEES-2023: the Integrated Database of the European Energy System"
            ),
            author=[
                "Mate Rozsai",
                "Marc Jaxa-Rozen",
                "Raffaele Salvucci",
                "Przemyslaw Sikora",
                "Juan Gea Bermudez",
                "Frederik Neuwahl",
            ],
            publication="JRC",
            publication_year=2026,
            url="https://publications.jrc.ec.europa.eu/repository/handle/JRC144707",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        return self._query_useful_thermal_energy_service()

    # -------- disk cache ------------------

    def _cache_path(self) -> Path:
        """Path to the on-disk cache file for the useful thermal energy
        service data."""
        if self.source_path is None:
            raise ValueError("source_path must be set to cache JRC-IDEES data.")
        return (
            self.source_path
            / "02-carrier"
            / "heat"
            / "jrc_idees"
            / "useful_thermal_energy_service.feather"
        )

    def _query_useful_thermal_energy_service(self) -> pd.DataFrame:
        """Return the useful thermal energy service (space and water
        heating) per node and sector, querying and caching it on first use.

        Downloading and parsing all JRC-IDEES country files is slow, so the
        result is persisted under
        ``source_path/02-carrier/jrc_idees/useful_thermal_energy_service.feather``.
        """
        cache_path = self._cache_path()

        if cache_path.exists() and not get_active_cache_settings().overwrite_jrc_idees:
            logger.info(
                "Loading cached JRC-IDEES thermal energy service data from "
                f"{cache_path}"
            )
            data = pd.read_feather(cache_path).set_index(["node", "sector", "category"])
            data.columns = data.columns.astype(int)
            return data

        logger.info(
            "Downloading JRC-IDEES thermal energy service data "
            "(this may take a while)..."
        )
        data = pd.concat(
            self._download_country_tes(country) for country in _JRC_IDEES_COUNTRIES
        )

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        reset = data.reset_index()
        reset.columns = reset.columns.astype(str)
        reset.to_feather(cache_path)
        return data

    def _download_country_tes(self, country: str) -> pd.DataFrame:
        """Download and parse the useful thermal energy service (space and
        water heating) for a single country, for the residential and
        tertiary sectors."""
        zip_url = f"{_JRC_IDEES_BASE_URL}JRC-IDEES-2023_{country}.zip"
        response = requests.get(zip_url)
        response.raise_for_status()

        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            with archive.open(f"JRC-IDEES-2023_Residential_{country}.xlsx") as file:
                residential = self._extract_tes_sheet(
                    pd.read_excel(file, sheet_name="RES_hh_tes")
                )
            with archive.open(f"JRC-IDEES-2023_Tertiary_{country}.xlsx") as file:
                tertiary = self._extract_tes_sheet(
                    pd.read_excel(file, sheet_name="SER_hh_tes")
                )

        data = pd.concat(
            {"residential": residential, "tertiary": tertiary}, names=["sector"]
        )
        return pd.concat({country: data}, names=["node"])

    def _extract_tes_sheet(self, sheet: pd.DataFrame) -> pd.DataFrame:
        """Extract the space- and water-heating useful thermal energy
        service rows from a JRC-IDEES ``*_hh_tes`` sheet, converted from
        ktoe (useful) to GWh."""
        category_col = sheet.columns[0]
        year_cols = [col for col in sheet.columns if isinstance(col, int)]

        data = sheet[[category_col, *year_cols]].rename(
            columns={category_col: "category"}
        )
        data = data[data["category"].isin(_JRC_IDEES_TES_ROWS)]
        data["category"] = data["category"].map(_JRC_IDEES_TES_ROWS)
        return data.set_index("category")[year_cols] * _KTOE2GWH

    # -------- methods ------------------------
    def get_demand(self, element: Element) -> pd.Series:
        """
        Get the demand of heat from the JRC-IDEES dataset.

        Args:
            element (Element): The element for which to get the demand.

        Returns:
            A pandas Series containing the demand data for the specified carrier.
        """
        data = self.data.copy()
        common_countries = data.index.get_level_values("node").isin(
            element.model.config.system.set_nodes
        )
        data = data.loc[common_countries, element.settings.time.time_series_year]
        return data

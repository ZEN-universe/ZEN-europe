from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

import pandas as pd
import requests
from zen_creator import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings
from zen_europe.utils.utils import convert_ISO3_to_ISO2

# The World Bank series is downloaded once and then read back from this
# directory, so that building a model does not depend on the World Bank API
# being reachable. Delete the cached file to pick up a newer data vintage.
_CACHE_DIRECTORY = ("01-energy_system", "worldbank_co2_emissions")

# emissions are reported in Mt, the carbon budget is accounted in Gt
_MT_PER_GT = 1e3

# row label of the world total, which is no NUTS0 node
WORLD = "World"


class WorldBankCO2Emissions(Dataset[pd.DataFrame]):
    """Historical CO2 emissions of the modeled countries and the world."""

    name = "worldbank_co2_emissions"

    # EN.GHG.CO2.MT.CE.AR5 is the EDGAR/IEA based CO2 series of the World
    # Development Indicators, excluding LULUCF, in Mt CO2 equivalent.
    URL = (
        "https://api.worldbank.org/v2/country/all/indicator/"
        "EN.GHG.CO2.MT.CE.AR5?format=json&per_page=32767"
    )
    CACHE_FILE = "worldbank_co2_emissions.csv"
    WORLD_CODE = "WLD"
    TIMEOUT = 60

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Carbon dioxide (CO2) emissions (total) excluding LULUCF",
            author=["World Bank"],
            publication="World Development Indicators",
            publication_year=datetime.now().year,
            url=("https://data.worldbank.org/indicator/EN.GHG.CO2.MT.CE.AR5"),
            note="Indicator EN.GHG.CO2.MT.CE.AR5, in Mt CO2 equivalent.",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            return None
        path = self.source_path.joinpath(*_CACHE_DIRECTORY)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ----- Load and format Data -----

    def _set_data(self) -> pd.DataFrame:
        """CO2 emissions in Mt, indexed by node, with the years as columns.

        The world total is in the row `World`, all other rows are NUTS0 nodes.
        """
        cache_path = self._cache_path()
        overwrite = get_active_cache_settings().overwrite_worldbank_co2_emissions
        if cache_path is not None and cache_path.exists() and not overwrite:
            data = pd.read_csv(cache_path, index_col="node")
            data.columns = data.columns.astype(int)
            data.columns.name = "year"
            return data

        data = self._download()
        if cache_path is not None:
            data.to_csv(cache_path)
        return data

    def _cache_path(self) -> Path | None:
        """The file the downloaded series is cached in."""
        return None if self.source_path is None else self.path / self.CACHE_FILE

    def _download(self) -> pd.DataFrame:
        """Download the indicator and reduce it to the modeled nodes and the world."""
        response = requests.get(self.URL, timeout=self.TIMEOUT)
        response.raise_for_status()
        header, observations = response.json()
        if int(header["pages"]) != 1:
            raise ValueError(
                f"The World Bank API returned {header['pages']} pages, but only "
                "the first one is read. Raise per_page in the request URL."
            )

        df = pd.DataFrame(observations)
        df["node"] = convert_ISO3_to_ISO2(df["countryiso3code"])
        df.loc[df["countryiso3code"] == self.WORLD_CODE, "node"] = WORLD
        df["year"] = df["date"].astype(int)
        df = df.dropna(subset=["node", "value"])

        data = df.pivot(index="node", columns="year", values="value").astype(float)
        data = data.sort_index(axis=1)
        if WORLD not in data.index:
            raise ValueError("The World Bank data does not contain the world total.")
        return data

    # ------ Outward facing functions ------

    def get_emissions_world(self, years: list[int] | None = None) -> pd.Series:
        """World CO2 emissions in Gt, indexed by year.

        Args:
            years (list[int] | None): Years to return, all years if None.
        """
        emissions = cast(pd.Series, self.data.loc[WORLD]) / _MT_PER_GT
        return emissions if years is None else emissions[years]

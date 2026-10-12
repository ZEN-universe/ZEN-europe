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
_CACHE_DIRECTORY = ("01-energy_system", "worldbank_population")

# row label of the world total, which is no NUTS0 node
WORLD = "World"


class WorldBankPopulation(Dataset[pd.DataFrame]):
    """Population estimates and projections of the modeled countries and the world."""

    name = "worldbank_population"

    URL = (
        "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL"
        "?source=40&format=json&per_page=32767"
    )
    CACHE_FILE = "worldbank_population.csv"
    WORLD_CODE = "WLD"
    TIMEOUT = 60

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Population estimates and projections",
            author=["World Bank"],
            publication="World Bank DataBank",
            publication_year=datetime.now().year,
            url=(
                "https://databank.worldbank.org/source/"
                "population-estimates-and-projections#"
            ),
            note="Indicator SP.POP.TOTL, total population in persons.",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            return None
        path = self.source_path.joinpath(*_CACHE_DIRECTORY)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ----- Load and format Data -----

    def _set_data(self) -> pd.DataFrame:
        """Population in persons, indexed by node, with the years as columns.

        The world total is in the row `World`, all other rows are NUTS0 nodes.
        """
        cache_path = self._cache_path()
        overwrite = get_active_cache_settings().overwrite_worldbank_population
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

    def get_population(
        self, nodes: list[str], years: list[int] | None = None
    ) -> pd.DataFrame:
        """Population of the given nodes, in persons, indexed by node.

        Args:
            nodes (list[str]): NUTS0 node names.
            years (list[int] | None): Years to return, all years if None.
        """
        missing = [node for node in nodes if node not in self.data.index]
        if missing:
            raise ValueError(
                f"No population data for the nodes {missing}. "
                f"Available nodes: {list(self.data.index)}"
            )
        population = self.data.loc[nodes]
        return population if years is None else population[years]

    def get_population_world(self, years: list[int] | None = None) -> pd.Series:
        """World population in persons, indexed by year.

        Args:
            years (list[int] | None): Years to return, all years if None.
        """
        population = cast(pd.Series, self.data.loc[WORLD])
        return population if years is None else population[years]

    def get_population_share(
        self, nodes: list[str], start_year: int, end_year: int
    ) -> float:
        """Share of the given nodes in the world population between two years.

        The share is the sum of the population over the years, so that a node
        counts by the person-years it contributes over the whole period.

        Args:
            nodes (list[str]): NUTS0 node names.
            start_year (int): First year of the period, inclusive.
            end_year (int): Last year of the period, inclusive.
        """
        years = list(range(start_year, end_year + 1))
        population = self.get_population(nodes, years).to_numpy().sum()
        population_world = self.get_population_world(years).to_numpy().sum()
        return float(population / population_world)

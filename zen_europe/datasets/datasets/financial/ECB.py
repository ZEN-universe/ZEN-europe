from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from zen_creator import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings

# The ECB series are downloaded once and then read back from this directory,
# so that building a model does not depend on the ECB API being reachable.
# Delete the cached file to pick up newer observations.
_CACHE_DIRECTORY = ("04-monetary", "ecb")


def _cache_directory(source_path: Path | str | None) -> Path | None:
    """The directory the ECB series are cached in, None without a source path."""
    if source_path is None:
        return None
    path = Path(source_path).joinpath(*_CACHE_DIRECTORY)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_cache(path: Path | None) -> pd.DataFrame | None:
    """Return the cached yearly series, or None if it has not been cached yet
    or the cache should be overwritten."""
    if path is None or not path.exists() or get_active_cache_settings().overwrite_ecb:
        return None
    return pd.read_csv(path, index_col="year")


def _write_cache(path: Path | None, data: pd.DataFrame) -> None:
    """Cache the yearly series, unless there is no source path to cache it in."""
    if path is not None:
        data.to_csv(path)


def _read_yearly_observations(url: str) -> pd.DataFrame:
    """Download an ECB series and return its monthly observations by year."""
    df = pd.read_csv(url, usecols=["TIME_PERIOD", "OBS_VALUE"])

    period_parts = df["TIME_PERIOD"].astype(str).str.split("-", n=1, expand=True)
    df["year"] = pd.to_numeric(period_parts[0], errors="raise").astype(int)
    df["month"] = pd.to_numeric(period_parts[1], errors="raise").astype(int)
    df["obs_value"] = pd.to_numeric(df["OBS_VALUE"], errors="raise").astype(float)

    if df.isna().values.any():
        raise ValueError(
            "Data contains NaN values after conversion. "
            "Please check the source data."
        )
    return df


class ECBInflation(Dataset[pd.DataFrame]):
    """Dataset class for ECB data."""

    name = "ecb_inflation"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="HICP - Overall index, Euro area, Monthly",
            author=["European Central Bank"],
            publication="European Central Bank",
            publication_year=datetime.now().year,
            url="https://data.ecb.europa.eu/",
        )

    URL = (
        "https://data-api.ecb.europa.eu/service/data/ICP/"
        "M.U2.N.000000.4.ANR?format=csvdata"
    )
    CACHE_FILE = "ecb_inflation.csv"

    def _set_path(self) -> Path | None:
        return _cache_directory(self.source_path)

    # ----- Property overwrites -----

    # ----- Load and format Data -----

    def _set_data(self) -> pd.DataFrame:
        """Method to get the inflation rate from ECB data."""
        cache_path = self._cache_path()
        cached = _read_cache(cache_path)
        if cached is not None:
            return cached

        # imported here because scipy is slow to import and this is the only
        # use of it, on the path that is skipped whenever the cache exists
        import scipy.stats as stats

        df = _read_yearly_observations(self.URL)
        df["inflation_factor"] = 1.0 + df["obs_value"] / 100.0

        inflation_data = df.groupby("year", sort=True)["inflation_factor"].agg(
            lambda values: float(stats.gmean(values.to_numpy(dtype=float)))
        )
        data = inflation_data.to_frame(name="inflation_rate")
        _write_cache(cache_path, data)
        return data

    def _cache_path(self) -> Path | None:
        """The file the downloaded series is cached in."""
        return None if self.source_path is None else self.path / self.CACHE_FILE

    # ------ Outward facing functions ------

    def get_inflation_rate(self, base_year: int, target_year: int) -> float:
        """Method to calculate the inflation rate between two years."""
        if base_year >= target_year:
            by = target_year
            ty = base_year
            exp = -1
        else:
            by = base_year
            ty = target_year
            exp = 1
        if ty - 1 not in self.data.index:
            logging.info(
                f"Target year {ty} is after the last available ECB year "
                f"{self.data.index[-1]}. Using {self.data.index[-1]} instead."
            )
            ty = self.data.index[-1] + 1
        inflation_rates = pd.to_numeric(
            self.data.loc[by : ty - 1, "inflation_rate"],
            errors="raise",
        )
        return float((inflation_rates.to_numpy(dtype=float).prod()) ** exp)


class ECBDollar2Euro(Dataset[pd.DataFrame]):
    """Dataset class for ECB data."""

    name = "ecb_dollar_to_euro"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="US dollar/Euro ECB reference exchange rate, Monthly",
            author=["European Central Bank"],
            publication="European Central Bank",
            publication_year=datetime.now().year,
            url="https://data.ecb.europa.eu/data/datasets/EXR/EXR.M.USD.EUR.SP00.A",
        )

    URL = (
        "https://data-api.ecb.europa.eu/service/data/EXR/"
        "M.USD.EUR.SP00.A?format=csvdata"
    )
    CACHE_FILE = "ecb_dollar_to_euro.csv"

    def _set_path(self) -> Path | None:
        return _cache_directory(self.source_path)

    # ----- Property overwrites -----

    # ----- Load and format Data -----

    def _set_data(self) -> pd.DataFrame:
        """Method to get the dollar-to-euro conversion rate from ECB data."""
        cache_path = self._cache_path()
        cached = _read_cache(cache_path)
        if cached is not None:
            return cached

        df = _read_yearly_observations(self.URL)
        euro2dollar = df.groupby("year")["obs_value"].mean()
        data = euro2dollar.to_frame(name="euro2dollar")
        _write_cache(cache_path, data)
        return data

    def _cache_path(self) -> Path | None:
        """The file the downloaded series is cached in."""
        return None if self.source_path is None else self.path / self.CACHE_FILE

    # ------ Outward facing functions ------

    def get_dollar2euro(self, year: int) -> float:
        """Method to calculate the dollar-to-euro conversion rate for a given year."""
        euro2dollar = float(self.data["euro2dollar"].loc[year])
        return 1 / euro2dollar

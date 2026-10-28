from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
import requests
from zen_creator import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings

# The workbook is downloaded once and then read back from this directory, so
# that building a model does not depend on the Global Carbon Budget download
# being reachable. Delete the cached file to pick up a newer data vintage.
_CACHE_DIRECTORY = ("01-energy_system", "global_carbon_budget")

logger = logging.getLogger(__name__)

SHEET = "Global Carbon Budget"
# row the column headers are on, 0-indexed, the sheet leads with explanatory
# text and source citations above the time series
_HEADER_ROW = 21
FOSSIL_COLUMN = "fossil emissions excluding carbonation"
LAND_USE_COLUMN = "land-use change emissions"

# Emissions are reported in GtC, the carbon budget is accounted in GtCO2.
_GTCO2_PER_GTC = 3.664


class GlobalCarbonBudget(Dataset[pd.Series]):
    """Global CO2 emissions from fossil fuels and land-use change."""

    name = "global_carbon_budget"

    # The dataset is republished under a new file id every edition, so the
    # URL has to be raised together with the version.
    URL = "https://globalcarbonbudget.org/download/2341/"
    VERSION = "2025"
    TIMEOUT = 60

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=f"Global Carbon Budget {self.VERSION}",
            author=["Friedlingstein, P. et al."],
            publication="Global Carbon Project",
            publication_year=int(self.VERSION),
            url="https://globalcarbonbudget.org/datahub/",
            note=(
                f"Sheet '{SHEET}', columns '{FOSSIL_COLUMN}' and "
                f"'{LAND_USE_COLUMN}' in GtC/yr, converted to GtCO2/yr."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            return None
        path = self.source_path.joinpath(*_CACHE_DIRECTORY)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ----- Load and format Data -----

    def _set_data(self) -> pd.Series:
        """Global CO2 emissions in Gt, indexed by year.

        Sums the fossil and land-use change emissions reported in GtC/yr and
        converts them to GtCO2/yr.
        """
        cache_path = self._cache_path()
        overwrite = get_active_cache_settings().overwrite_global_carbon_budget
        if cache_path is not None and cache_path.exists() and not overwrite:
            data = pd.read_csv(cache_path, index_col="year")["emissions"]
            data.index = data.index.astype(int)
            return data

        data = self._download()
        if cache_path is not None:
            data.to_csv(cache_path)
        return data

    def _cache_path(self) -> Path | None:
        """The file the reduced series is cached in."""
        return None if self.source_path is None else self.path / f"{self.name}.csv"

    def _download(self) -> pd.Series:
        """Download the workbook and sum the fossil and land-use emissions."""
        response = requests.get(self.URL, timeout=self.TIMEOUT)
        response.raise_for_status()
        table = pd.read_excel(
            io.BytesIO(response.content), sheet_name=SHEET, header=_HEADER_ROW
        )

        emissions = (table[FOSSIL_COLUMN] + table[LAND_USE_COLUMN]) * _GTCO2_PER_GTC
        emissions.index = table["Year"].astype(int)
        emissions.index.name = "year"
        emissions.name = "emissions"
        return emissions.sort_index()

    # ------ Outward facing functions ------

    # def get_historic_emissions(
    #     self,
    #     start_year: int,
    #     end_year: int,
    #     extrapolate_missing_years: bool = False,
    # ) -> pd.Series:
    #     """Global CO2 emissions in Gt between two years, inclusive.

    #     Args:
    #         start_year (int): First year of the period.
    #         end_year (int): Last year of the period.
    #         extrapolate_missing_years (bool): If True, years after the last
    #             reported year are filled with a linear fit of the last
    #             `EXTRAPOLATION_YEARS` reported years. If False, missing years
    #             raise an error.
    #     """
    #     missing = [
    #         year for year in (start_year, end_year) if year not in self.data.index
    #     ]
    #     last_year = int(self.data.index.max())
    #     only_after_last_year = all(year > last_year for year in missing)
    #     if missing and not (extrapolate_missing_years and only_after_last_year):
    #         raise ValueError(
    #             f"The Global Carbon Budget does not report the years {missing}. "
    #             f"Available years: {self.data.index.min()}-{last_year}."
    #         )
    #     if not missing:
    #         return self.data.loc[start_year:end_year]

    #     extrapolated_years = range(last_year + 1, end_year + 1)
    #     year_str = (
    #         f"{extrapolated_years[0]}-{end_year}"
    #         if len(extrapolated_years) > 1
    #         else str(extrapolated_years[0])
    #     )
    #     logger.warning(
    #         f"The Global Carbon Budget {self.VERSION} reports emissions until "
    #         f"{last_year}. Extrapolating values for {year_str} "
    #         f"linearly from the last {self.EXTRAPOLATION_YEARS} years."
    #     )
    #     reference = self.data.loc[last_year - self.EXTRAPOLATION_YEARS + 1 :]
    #     slope, intercept = np.polyfit(reference.index, reference.values, deg=1)
    #     extrapolated = pd.Series(
    #         [slope * year + intercept for year in extrapolated_years],
    #         index=pd.Index(extrapolated_years, name=self.data.index.name),
    #         name=self.data.name,
    #     )
    #     return pd.concat([self.data, extrapolated]).loc[start_year:end_year]

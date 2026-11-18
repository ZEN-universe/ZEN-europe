from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import cast

import pandas as pd
import requests
from zen_creator import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings

# The workbook is downloaded once, reduced to a single pollutant and then read
# back from this directory, so that building a model does not depend on the
# DESNZ download being reachable. Delete the cached file to rebuild it.
_CACHE_DIRECTORY = ("01-energy_system", "desnz_ghg_inventory")

# Emissions are reported in Mt, the carbon budget is accounted in Gt.
_MT_PER_GT = 1e3

# The UK reports along its own territorial emission statistics (TES) hierarchy,
# not along the UNFCCC categories that the EEA inventory uses.
INDEX_NAMES = ["tes_sector", "tes_subsector", "tes_category"]

# rows that are always included, the counterpart of public electricity and heat
# plus commercial and residential in the UNFCCC categories
BASE_CATEGORIES = [
    ("Electricity supply total", "Electricity supply total", "Total"),
    ("Buildings and product uses total", "Buildings and product uses total", "Total"),
]
# The grand total row is spelled "Grand total" on the all greenhouse gas sheet
# and "Grand Total" on the CO2 sheet of the same workbook, so it is normalized.
GRAND_TOTAL = ("Grand total", "Grand total", "Total")

SECTOR_CATEGORIES = {
    "passenger_transport": [("Domestic transport", "Road", "Passenger cars")],
    "truck_transport": [("Domestic transport", "Road", "HGVs")],
    "refining": [("Fuel supply", "Oil and gas supply", "Oil refineries")],
    "cement": [("Industry", "Industrial processes", "Cement production")],
    "aviation": [("Domestic transport", "Civil aviation", "Civil aviation")],
    "shipping": [
        ("Domestic transport", "Waterborne", "Shipping - coastal"),
        ("Domestic transport", "Waterborne", "Shipping - other"),
    ],
    "steel": [
        ("Industry", "Industrial processes", "Iron and steel production processes"),
        ("Industry", "Industrial fuel combustion", "Iron and steel production"),
    ],
    # glass and ceramics processes
    "glass": [("Industry", "Industrial processes", "Glass production")],
    "ceramic": [
        ("Industry", "Industrial processes", "Bricks production"),
        ("Industry", "Industrial processes", "Other ceramics"),
    ],
}
# The chemical industry categories cover methanol and ammonia together. Other
# industrial combustion is wider than the two, it also holds pulp and paper.
CHEMICALS_CATEGORIES = [
    ("Industry", "Industrial processes", "Ammonia production"),
    ("Industry", "Industrial processes", "Other - chemical industry"),
    ("Industry", "Industrial fuel combustion", "Other industrial combustion"),
]
CHEMICALS_SECTORS = ["methanol", "ammonia"]

# International bunkers are a memo item of the inventory rather than part of the
# territorial total, and are stored under a sector of their own.
INTERNATIONAL_SECTOR = "Memo items"
INTERNATIONAL_SUBSECTOR = "International bunkers"
INTERNATIONAL_CATEGORIES = {
    "aviation": "International aviation bunkers",
    "shipping": "International shipping bunkers",
}

# first year of the time series
DESNZ_START_YEAR = 1990


def _read_sheet(workbook: pd.ExcelFile, sheet: str, first_column: str) -> pd.DataFrame:
    """Read a sheet, finding the header row by its first column label.

    The number of explanatory rows above the table changes between editions,
    so the header row is searched for rather than hard coded.
    """
    raw = pd.read_excel(workbook, sheet_name=sheet, header=None)
    labels = raw[0].astype(str).str.strip().str.casefold()
    matches = labels[labels == first_column.casefold()]
    if matches.empty:
        raise ValueError(
            f"Sheet '{sheet}' has no header row starting with '{first_column}'."
        )
    return pd.read_excel(workbook, sheet_name=sheet, header=int(matches.index[0]))


class DESNZGreenhouseGasInventory(Dataset[pd.DataFrame]):
    """CO2 emissions of the UK, as reported in the DESNZ emission statistics."""

    name = "desnz_ghg_inventory_co2"

    # sheet of the territorial emissions and the memo item gas, per pollutant
    SHEET = "1.3"
    GAS = "Carbon dioxide (CO2)"

    INTERNATIONAL_SHEET = "5.1"
    # The asset URL carries a media hash that changes with every publication,
    # so it has to be raised together with the final year of the statistics.
    URL = (
        "https://assets.publishing.service.gov.uk/media/6982294819d3abdb495f37ce"
        "/final-greenhouse-gas-emissions-tables-2024.xlsx"
    )
    FINAL_YEAR = 2024
    TIMEOUT = 120

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                f"Final UK greenhouse gas emissions national statistics: "
                f"1990 to {self.FINAL_YEAR}"
            ),
            author=["Department for Energy Security and Net Zero"],
            publication="GOV.UK",
            publication_year=datetime.now().year,
            url=(
                "https://www.gov.uk/government/statistics/"
                f"final-uk-greenhouse-gas-emissions-statistics-1990-to-{self.FINAL_YEAR}"
            ),
            note=(
                f"Data tables, sheet {self.SHEET} for the territorial emissions "
                f"and sheet {self.INTERNATIONAL_SHEET} for the international "
                f"bunkers, gas {self.GAS}."
            ),
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            return None
        path = self.source_path.joinpath(*_CACHE_DIRECTORY)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ----- Load and format Data -----

    def _set_data(self) -> pd.DataFrame:
        """Emissions of one pollutant, indexed by the TES hierarchy.

        The years are the columns and the values are in Mt, as reported. The
        international bunkers are appended under the sector `Memo items`.
        """
        cache_path = self._cache_path()
        overwrite = get_active_cache_settings().overwrite_desnz_ghg_inventory
        if cache_path is not None and cache_path.exists() and not overwrite:
            data = pd.read_csv(cache_path, index_col=INDEX_NAMES)
            data.columns = data.columns.astype(int)
            data.columns.name = "year"
            return data

        data = self._download()
        if cache_path is not None:
            data.to_csv(cache_path)
        return data

    def _cache_path(self) -> Path | None:
        """The file the reduced workbook is cached in."""
        return None if self.source_path is None else self.path / f"{self.name}.csv"

    def _download(self) -> pd.DataFrame:
        """Download the workbook and reduce it to a single pollutant."""
        response = requests.get(self.URL, timeout=self.TIMEOUT)
        response.raise_for_status()
        workbook = pd.ExcelFile(io.BytesIO(response.content))

        territorial = self._read_territorial(workbook)
        international = self._read_international(workbook)
        data = pd.concat([territorial, international])
        data.index.names = INDEX_NAMES
        return data.sort_index(axis=1)

    def _read_territorial(self, workbook: pd.ExcelFile) -> pd.DataFrame:
        """The territorial emissions, indexed by the three TES levels."""
        df = _read_sheet(workbook, self.SHEET, "TES sector")
        levels = list(df.columns[:3])
        is_total = df[levels[0]].astype(str).str.strip().str.casefold() == "grand total"
        df.loc[is_total, levels[0]] = GRAND_TOTAL[0]
        # The sector and subsector are only spelled out on the first row of each
        # block, and the total rows carry the sector alone, so the two levels are
        # filled from the left first and from the row above second.
        df[levels[:2]] = df[levels[:2]].ffill(axis=1)
        df[levels[:2]] = df[levels[:2]].ffill()
        # the grand total row has no category of its own
        df[levels[2]] = df[levels[2]].fillna("Total")

        df = df.set_index(levels)
        df.columns = df.columns.astype(int)
        if df.index.has_duplicates:
            raise ValueError("The workbook reports a TES category more than once.")
        if GRAND_TOTAL not in df.index:
            raise ValueError(f"The workbook has no grand total row {GRAND_TOTAL}.")
        return df

    def _read_international(self, workbook: pd.ExcelFile) -> pd.DataFrame:
        """The international bunkers of one gas, indexed like the TES levels."""
        df = _read_sheet(workbook, self.INTERNATIONAL_SHEET, "Memo item")
        memo, gas = df.columns[0], df.columns[1]
        df[memo] = df[memo].ffill()

        categories = list(INTERNATIONAL_CATEGORIES.values())
        df = df[df[memo].isin(categories) & (df[gas] == self.GAS)]
        missing = [c for c in categories if c not in df[memo].values]
        if missing:
            raise ValueError(f"The workbook has no bunker rows for {missing}.")

        df = df.set_index(memo).drop(columns=gas)
        df.columns = df.columns.astype(int)
        df.index = pd.MultiIndex.from_tuples(
            [
                (INTERNATIONAL_SECTOR, INTERNATIONAL_SUBSECTOR, memo_item)
                for memo_item in df.index
            ]
        )
        return df

    # ------ Outward facing functions ------

    def get_sector_categories(self, sectors: list[str]) -> list[tuple[str, str, str]]:
        """The TES categories covered by the modeled sectors.

        The international bunkers are included for aviation and shipping, as
        they are for the EEA inventory.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
        """
        categories = list(BASE_CATEGORIES)
        for sector in sectors:
            categories += SECTOR_CATEGORIES.get(sector, [])
        if all(sector in sectors for sector in CHEMICALS_SECTORS):
            categories += CHEMICALS_CATEGORIES
        elif any(sector in sectors for sector in CHEMICALS_SECTORS):
            raise ValueError(
                f"Both {CHEMICALS_SECTORS} must be modeled to include the "
                "chemical industry emissions, but only one is selected."
            )
        categories += self.get_international_categories(sectors)
        return categories

    def get_international_categories(
        self, sectors: list[str]
    ) -> list[tuple[str, str, str]]:
        """The international bunker categories covered by the modeled sectors.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
        """
        return [
            (INTERNATIONAL_SECTOR, INTERNATIONAL_SUBSECTOR, category)
            for sector, category in INTERNATIONAL_CATEGORIES.items()
            if sector in sectors
        ]

    def get_emissions_sectors(
        self,
        sectors: list[str],
        start_year: int = DESNZ_START_YEAR,
    ) -> pd.DataFrame:
        """Emissions of the modeled sectors in Gt, by TES category.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
            start_year (int): First year of the time series.
        """
        categories = self.get_sector_categories(sectors)
        emissions = self._select(categories)
        return emissions.loc[:, start_year:] / _MT_PER_GT

    def get_emissions_total(
        self,
        sectors: list[str],
        start_year: int = DESNZ_START_YEAR,
    ) -> pd.Series:
        """Total emissions of the UK in Gt, by year.

        The international bunkers are added to the territorial total whenever
        aviation or shipping is modeled, because only then are they part of the
        sector emissions.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
            start_year (int): First year of the time series.
        """
        emissions = cast(pd.Series, self.data.loc[GRAND_TOTAL, :])
        international = self.get_international_categories(sectors)
        if international:
            bunkers = self._select(international)
            emissions = emissions + bunkers.sum()
        return emissions.loc[start_year:] / _MT_PER_GT

    def get_emissions(
        self,
        sectors: list[str],
        start_year: int = DESNZ_START_YEAR,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Sector emissions and total emissions of the UK, both in Gt.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
            start_year (int): First year of the time series.
        """
        emissions_sectors = self.get_emissions_sectors(sectors, start_year)
        emissions_total = self.get_emissions_total(sectors, start_year)
        return emissions_sectors, emissions_total

    def get_sector_share(
        self,
        sectors: list[str],
        start_year: int = DESNZ_START_YEAR,
    ) -> pd.Series:
        """Share of the modeled sectors in the UK emissions, by year.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
            start_year (int): First year of the time series.
        """
        emissions_sectors, emissions_total = self.get_emissions(sectors, start_year)
        return emissions_sectors.sum() / emissions_total

    # ------ Helpers ------

    def _select(self, categories: list[tuple[str, str, str]]) -> pd.DataFrame:
        """The emissions of the given TES categories, in Mt."""
        missing = [c for c in categories if c not in self.data.index]
        if missing:
            raise ValueError(f"The workbook does not report the categories {missing}.")
        return self.data.loc[categories]


class DESNZGreenhouseGasInventoryAllGHG(DESNZGreenhouseGasInventory):
    """All UK greenhouse gas emissions in CO2 equivalents."""

    name = "desnz_ghg_inventory_all_ghg"

    SHEET = "1.2"
    GAS = "Total"

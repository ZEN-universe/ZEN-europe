from __future__ import annotations

import logging
import zipfile
from functools import cached_property
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
from zen_europe.utils.industry import IDEES_EU

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

# regions of the industry workbooks (glass, ceramic, paper and food sectors): the
# EU27 aggregate and the member states that are model nodes (Cyprus and Malta are
# not)
_JRC_IDEES_INDUSTRY_REGIONS = sorted(
    [country for country in _JRC_IDEES_COUNTRIES if country not in ("CY", "MT")]
    + [IDEES_EU]
)
_JRC_IDEES_INDUSTRY_SHEETS = ["NMM", "PPA", "NMM_fec", "PPA_fec", "FBT_fec"]
# the year columns of the first block of each sheet
_JRC_IDEES_INDUSTRY_FIRST_YEAR = 2000
_JRC_IDEES_INDUSTRY_LAST_YEAR = 2023
# sheet and rows of the production capacity and output per sector
_JRC_IDEES_CAPACITY_ROWS = {
    "glass": ("NMM", ["Glass production  (kt)"]),
    "ceramic": ("NMM", ["Ceramics & other NMM (kt bricks eq.)"]),
    "paper": (
        "PPA",
        [
            "Pulp production (kt)",
            "Paper production  (kt)",
            "Printing and media reproduction (kt paper eq.)",
        ],
    ),
}
# headers of the production sections in the NMM and PPA sheets
_JRC_IDEES_PRODUCTION_HEADERS = {
    "Physical output (kt)": "physical_output",
    "Installed capacity (kt production)": "installed_capacity",
}
# sheet and parent rows of the thermal final energy consumption per sector
_JRC_IDEES_THERMAL_ROWS = {
    "glass": ("NMM_fec", ["Glass: Thermal melting tank", "Glass: Annealing - thermal"]),
    "ceramic": (
        "NMM_fec",
        [
            "Ceramics: Thermal drying and sintering",
            "Ceramics: Steam drying and sintering",
            "Ceramics: Thermal kiln",
            "Ceramics: Thermal furnace",
        ],
    ),
    "paper": (
        "PPA_fec",
        [
            "Paper: Stock preparation - Thermal",
            "Paper: Paper machine - Steam use",
            "Paper: Product finishing - Steam use",
        ],
    ),
    "food": (
        "FBT_fec",
        [
            "Food: Direct Heat - Thermal",
            "Food: Process Heat - Thermal",
            "Food: Steam processing",
            "Food: Thermal drying",
            "Food: Steam drying",
            "Food: Steam cooling",
        ],
    ),
}
_JRC_IDEES_THERMAL_CARRIERS = {
    "Solids",
    "Refinery gas",
    "LPG",
    "Diesel oil and liquid biofuels",
    "Fuel oil",
    "Other liquids",
    "Natural gas and biogas",
    "Derived gases",
    "Biomass and waste",
    "Distributed steam",
}
# model carrier of the JRC-IDEES thermal carriers, per use; carriers that are not
# mapped are summed as "other"
_JRC_IDEES_FUEL_MAPPINGS = {
    # fuel inputs of the production technologies
    "production": {
        "Natural gas and biogas": "natural_gas",
        "Solids": "hard_coal",
        "Biomass and waste": "biomass",
        "Other liquids": "oil",
    },
    # boiler fuels; biomass and waste are one carrier in JRC-IDEES
    "boiler": {
        "Natural gas and biogas": "natural_gas",
        "Solids": "coal",
        "Derived gases": "coal",
        "LPG": "oil",
        "Diesel oil and liquid biofuels": "oil",
        "Fuel oil": "oil",
        "Other liquids": "oil",
        "Refinery gas": "oil",
        "Biomass and waste": "biomass_and_waste",
    },
}


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
            doi="10.2760/6945021",
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

    # -------- industry: disk cache and download ------------------

    @cached_property
    def _industry(self) -> dict[str, pd.DataFrame]:
        """Thermal final energy consumption (ktoe) and production (kt) of the
        glass, ceramic, paper and food sectors, querying and caching them on
        first use.

        The industry workbooks are part of the same country files as the
        thermal energy service data; they are cached separately under
        ``source_path/02-carrier/industry/jrc_idees/``.
        """
        index_names = {
            "thermal": ["node", "sector", "carrier"],
            "production": ["node", "sector", "quantity"],
        }
        cache_paths = {name: self._industry_cache_path(name) for name in index_names}
        if all(path.exists() for path in cache_paths.values()) and (
            not get_active_cache_settings().overwrite_jrc_idees
        ):
            logger.info("Loading cached JRC-IDEES industry data")
            data = {}
            for name, path in cache_paths.items():
                frame = pd.read_feather(path).set_index(index_names[name])
                frame.columns = frame.columns.astype(int)
                data[name] = frame
            return data

        logger.info("Downloading JRC-IDEES industry data (this may take a while)...")
        thermal = {}
        production = {}
        for region in _JRC_IDEES_INDUSTRY_REGIONS:
            sheets = self._download_industry_sheets(region)
            for sector, (sheet, parent_rows) in _JRC_IDEES_THERMAL_ROWS.items():
                thermal[(region, sector)] = self._extract_thermal(
                    sheets[sheet], parent_rows
                )
            for sector, (sheet, rows) in _JRC_IDEES_CAPACITY_ROWS.items():
                production[(region, sector)] = self._extract_production(
                    sheets[sheet], rows
                )
        data = {
            "thermal": pd.concat(thermal, names=index_names["thermal"]),
            "production": pd.concat(production, names=index_names["production"]),
        }
        for name, path in cache_paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            reset = data[name].reset_index()
            reset.columns = reset.columns.astype(str)
            reset.to_feather(path)
        return data

    def _industry_cache_path(self, name: str) -> Path:
        """Path to the on-disk cache file of the industry data `name`."""
        if self.source_path is None:
            raise ValueError("source_path must be set to cache JRC-IDEES data.")
        return (
            self.source_path
            / "02-carrier"
            / "industry"
            / "jrc_idees"
            / f"industry_{name}.feather"
        )

    def _download_industry_sheets(self, region: str) -> dict[str, pd.DataFrame]:
        """Download the industry workbook of a region and return its sheets, with
        the first block of year columns and the row labels as index."""
        zip_url = f"{_JRC_IDEES_BASE_URL}JRC-IDEES-2023_{region}.zip"
        response = requests.get(zip_url)
        response.raise_for_status()

        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            with archive.open(f"JRC-IDEES-2023_Industry_{region}.xlsx") as file:
                sheets = pd.read_excel(
                    file, sheet_name=_JRC_IDEES_INDUSTRY_SHEETS, header=None
                )
        return {sheet: self._extract_years(df) for sheet, df in sheets.items()}

    @staticmethod
    def _extract_years(sheet: pd.DataFrame) -> pd.DataFrame:
        """Return the first block of year columns, with the row labels as index."""
        first, last = _JRC_IDEES_INDUSTRY_FIRST_YEAR, _JRC_IDEES_INDUSTRY_LAST_YEAR
        data = sheet.iloc[:, 1 : last - first + 2]
        data.columns = range(first, last + 1)
        data.index = sheet[0]
        return data

    @staticmethod
    def _extract_thermal(sheet: pd.DataFrame, parent_rows: list[str]) -> pd.DataFrame:
        """Sum the energy carrier rows below the parent rows of a sector.

        The first occurrence of a parent row is the consumption in ktoe, followed
        directly by its energy carrier rows.
        """
        labels = list(sheet.index)
        carrier_rows = []
        for parent in parent_rows:
            row = labels.index(parent) + 1
            while row < len(labels) and labels[row] in _JRC_IDEES_THERMAL_CARRIERS:
                carrier_rows.append(row)
                row += 1
        data = sheet.iloc[carrier_rows].astype(float)
        return data.groupby(level=0, sort=False).sum(min_count=1)

    @staticmethod
    def _extract_production(sheet: pd.DataFrame, rows: list[str]) -> pd.DataFrame:
        """Sum the sector's rows in the physical output and installed capacity
        sections."""
        labels = list(sheet.index)
        data = {}
        for header, quantity in _JRC_IDEES_PRODUCTION_HEADERS.items():
            start = labels.index(header) + 1
            # a section ends at the next "(kt production)" header
            end = next(
                (
                    i
                    for i in range(start, len(labels))
                    if isinstance(labels[i], str)
                    and labels[i].endswith("(kt production)")
                ),
                len(labels),
            )
            section = sheet.iloc[start:end]
            data[quantity] = section.loc[rows].astype(float).sum()
        return pd.DataFrame(data).T

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

    def get_industry_thermal_final_energy(self, sector: str, year: int) -> pd.DataFrame:
        """
        Get the thermal final energy consumption of an industry sector.

        Args:
            sector (str): The industry sector (glass, ceramic, paper or food).
            year (int): The year of the data.

        Returns:
            pd.DataFrame: Consumption in ktoe, indexed by node, one column per
                energy carrier.
        """
        data = self._industry["thermal"].xs(sector, level="sector")[year]
        if data.isna().any():
            raise ValueError(f"No {year} value for all thermal carriers of {sector}.")
        # carriers not reported for a node are not consumed there
        return data.unstack("carrier", fill_value=0.0)

    def get_industry_thermal_final_energy_by_fuel(
        self, sector: str, year: int, use: str
    ) -> pd.DataFrame:
        """
        Get the thermal final energy consumption of an industry sector per model
        fuel.

        Args:
            sector (str): The industry sector (glass, ceramic, paper or food).
            year (int): The year of the data.
            use (str): The fuel mapping, "production" (fuel inputs of the
                production technologies) or "boiler" (boiler fuels).

        Returns:
            pd.DataFrame: Consumption in ktoe, indexed by node, one column per
                model fuel; carriers without a fuel of this use are summed as
                "other".
        """
        mapping = _JRC_IDEES_FUEL_MAPPINGS[use]
        thermal = self.get_industry_thermal_final_energy(sector, year)
        fuels = thermal.columns.map(lambda carrier: mapping.get(carrier, "other"))
        return thermal.T.groupby(fuels, sort=False).sum().T

    def get_industry_installed_capacity(self, sector: str, year: int) -> pd.Series:
        """Installed production capacity (kt) of an industry sector per node."""
        return self._industry["production"].xs(
            (sector, "installed_capacity"), level=["sector", "quantity"]
        )[year]

    def get_industry_physical_output(self, sector: str, year: int) -> pd.Series:
        """Physical production output (kt) of an industry sector per node."""
        return self._industry["production"].xs(
            (sector, "physical_output"), level=["sector", "quantity"]
        )[year]

    def get_industry_capacity_utilisation(
        self, sectors: tuple[str, ...], year: int
    ) -> float:
        """Mean EU27 capacity utilisation (physical output / installed capacity) of
        the industry sectors `sectors`."""
        utilisation = [
            self.get_industry_physical_output(sector, year)["EU27"]
            / self.get_industry_installed_capacity(sector, year)["EU27"]
            for sector in sectors
        ]
        return float(sum(utilisation) / len(utilisation))

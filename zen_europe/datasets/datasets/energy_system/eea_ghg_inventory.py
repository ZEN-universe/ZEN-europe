from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from zen_creator import Dataset
from zen_creator.datasets.datasets.metadata import MetaData

from zen_europe.settings.cache import get_active_cache_settings

# The inventory is downloaded once, reduced to a single pollutant and then read
# back from this directory, so that building a model does not depend on the EEA
# datastore being reachable. Delete the cached file to pick up a newer version.
_CACHE_DIRECTORY = ("01-energy_system", "eea_ghg_inventory")

# columns of the UNFCCC table that are read, the file has 18 in total
_COLUMNS = [
    "Country_code",
    "Pollutant_name",
    "Sector_code",
    "Unit",
    "Year",
    "emissions",
]

# Emissions are reported in Gg, the carbon budget is accounted in Gt.
_GG_PER_GT = 1e6

# UNFCCC sector codes of the sectors that ZEN-europe models. The codes are
# stable across inventory versions, the sector names are not: up to v27 they
# read "1.A.1.a - Public Electricity and Heat Production" and from v30 on
# "1.A.1.a. Public electricity and heat production".
COMMERCIAL_AND_RESIDENTIAL_CODES = ["1.A.4.a", "1.A.4.b"]
PUBLIC_ELECTRICITY_AND_HEAT_CODE = "1.A.1.a"
ENERGY_INDUSTRIES_CODE = "1.A.1"
SECTOR_CODES = {
    "passenger_transport": ["1.A.3.b.i"],
    "truck_transport": ["1.A.3.b.iii"],
    "refining": ["1.A.1.b"],
    "cement": ["1.A.2.f", "2.A"],
    "aviation": ["1.A.3.a", "1.D.1.a"],
    "shipping": ["1.A.3.d", "1.D.1.b"],
    "steel": ["1.A.2.a", "2.C.1"],
    # glass and ceramics combustion and processes are already part of 1.A.2.f
    # and 2.A of cement
    "paper": ["1.A.2.d"],
    # all of 1.A.2.e, although the modeled food sub-processes cover only about
    # 58 % of the JRC-IDEES food thermal energy, so the budget is slightly generous
    "food": ["1.A.2.e"],
}
# the chemical industry categories cover methanol and ammonia together
CHEMICALS_CODES = ["1.A.2.c", "2.B"]
CHEMICALS_SECTORS = ["methanol", "ammonia"]

# international aviation and navigation, which are reported as memo items and
# are therefore not part of the national total
INTERNATIONAL_TRANSPORT_CODES = ["1.D.1.a", "1.D.1.b"]
# net national total, so including LULUCF
TOTAL_CODE = "Sectors/Totals_incl"

# first year of the time series, the inventory reports back to 1985 but only
# the years from 1990 on are reported by every country
UNFCCC_START_YEAR = 1990


class EEAGreenhouseGasInventory(Dataset[pd.DataFrame]):
    """CO2 emissions of the European countries, as reported to the UNFCCC."""

    name = "eea_ghg_inventory_co2"

    # pollutant and unit as they are spelled in the UNFCCC table
    POLLUTANT = "CO2"
    UNIT = "Gg"

    # The dataset is a folder in the public EEA datastore. The version is part
    # of the folder and file name, so both have to be raised together to move
    # to a newer inventory.
    VERSION_FOLDER = "eea_t_national-emissions-reported_p_2026_v02_r00"
    CSV_FILE = "UNFCCC_v32.csv"
    TIMEOUT = 60
    CHUNK_SIZE = 500_000

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "GovReg: National emissions reported to the UNFCCC and to the "
                "EU under the Governance Regulation"
            ),
            author=["European Environment Agency"],
            publication="EEA Datahub",
            publication_year=datetime.now().year,
            url=(
                "https://www.eea.europa.eu/en/datahub/datahubitem-view/"
                "3b7fe76c-524a-439a-bfd2-a6e4046302a2"
            ),
            note=f"{self.CSV_FILE}, pollutant {self.POLLUTANT} in {self.UNIT}.",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is None:
            return None
        path = self.source_path.joinpath(*_CACHE_DIRECTORY)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def url(self) -> str:
        """The URL the inventory is downloaded from."""
        return (
            f"https://sdi.eea.europa.eu/datastore/public/{self.VERSION_FOLDER}"
            f"/CSV/{self.CSV_FILE}"
        )

    # ----- Load and format Data -----

    def _set_data(self) -> pd.DataFrame:
        """Emissions of one pollutant, indexed by sector code and node.

        The years are the columns and the values are in Gg, as reported. The
        nodes are the reporting countries, with Greece renamed from GR to EL.
        """
        cache_path = self._cache_path()
        overwrite = get_active_cache_settings().overwrite_eea_ghg_inventory
        if cache_path is not None and cache_path.exists() and not overwrite:
            data = pd.read_csv(cache_path, index_col=["sector_code", "node"])
            data.columns = data.columns.astype(int)
            data.columns.name = "year"
            return data

        data = self._download()
        if cache_path is not None:
            data.to_csv(cache_path)
        return data

    def _cache_path(self) -> Path | None:
        """The file the reduced inventory is cached in."""
        return None if self.source_path is None else self.path / f"{self.name}.csv"

    def _download(self) -> pd.DataFrame:
        """Download the inventory and reduce it to a single pollutant.

        The full table is around 200 MB and covers every pollutant, so it is
        filtered while it is streamed rather than kept in memory as a whole.
        """
        with requests.get(self.url, stream=True, timeout=self.TIMEOUT) as response:
            response.raise_for_status()
            response.raw.decode_content = True
            reader = pd.read_csv(
                response.raw,
                usecols=_COLUMNS,
                chunksize=self.CHUNK_SIZE,
                encoding="utf-8-sig",
                low_memory=False,
            )
            df = pd.concat(
                chunk[
                    (chunk["Pollutant_name"] == self.POLLUTANT)
                    & (chunk["Unit"] == self.UNIT)
                ]
                for chunk in reader
            )
        if df.empty:
            raise ValueError(
                f"The inventory holds no rows for pollutant '{self.POLLUTANT}' "
                f"in '{self.UNIT}'."
            )

        # the year column holds notation keys such as "Base year" in some versions
        df = df[df["Year"].astype(str).str.isnumeric()]
        df["Year"] = df["Year"].astype(int)
        df["emissions"] = pd.to_numeric(df["emissions"], errors="coerce")
        df.loc[df["Country_code"] == "GR", "Country_code"] = "EL"

        df = df.rename(
            columns={
                "Sector_code": "sector_code",
                "Country_code": "node",
                "Year": "year",
            }
        )
        index = ["sector_code", "node", "year"]
        if df.duplicated(subset=index).any():
            raise ValueError(
                "The inventory reports a sector, node and year more than once."
            )
        data = df.pivot(index=index[:2], columns="year", values="emissions")
        return data.sort_index(axis=1)

    # ------ Outward facing functions ------

    def get_sector_codes(self, sectors: list[str]) -> list[str]:
        """The UNFCCC sector codes covered by the modeled sectors.

        A code shared by several sectors is returned once, so that its
        emissions are not counted twice.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
        """
        codes = [PUBLIC_ELECTRICITY_AND_HEAT_CODE]
        codes += COMMERCIAL_AND_RESIDENTIAL_CODES
        for sector in sectors:
            codes += SECTOR_CODES.get(sector, [])
        if all(sector in sectors for sector in CHEMICALS_SECTORS):
            codes += CHEMICALS_CODES
        elif any(sector in sectors for sector in CHEMICALS_SECTORS):
            raise ValueError(
                f"Both {CHEMICALS_SECTORS} must be modeled to include the "
                "chemical industry emissions, but only one is selected."
            )
        return list(dict.fromkeys(codes))

    def get_emissions_sectors(
        self,
        sectors: list[str],
        nodes: list[str],
        start_year: int = UNFCCC_START_YEAR,
    ) -> pd.DataFrame:
        """Emissions of the modeled sectors in Gt, by sector code and node.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
            nodes (list[str]): NUTS0 node names, those without an inventory are
                skipped.
            start_year (int): First year of the time series.
        """
        codes = self.get_sector_codes(sectors)
        emissions = self._select(codes, nodes)
        return emissions.loc[:, start_year:] / _GG_PER_GT

    def get_emissions_total(
        self,
        nodes: list[str],
        include_international_transport: bool = True,
        start_year: int = UNFCCC_START_YEAR,
    ) -> pd.Series:
        """Total net emissions of the nodes in Gt, summed by year.

        Args:
            nodes (list[str]): NUTS0 node names, those without an inventory are
                skipped.
            include_international_transport (bool): Whether to add international
                aviation and navigation, which the national total leaves out.
            start_year (int): First year of the time series.
        """
        codes = [TOTAL_CODE]
        if include_international_transport:
            codes += INTERNATIONAL_TRANSPORT_CODES
        emissions = self._select(codes, nodes).sum()
        return emissions.loc[start_year:] / _GG_PER_GT

    def get_emissions(
        self,
        sectors: list[str],
        nodes: list[str],
        use_only_public_electricity_and_heat: bool = True,
        include_international_transport: bool = True,
        start_year: int = UNFCCC_START_YEAR,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Sector emissions and total emissions of the nodes, both in Gt.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
            nodes (list[str]): NUTS0 node names, those without an inventory are
                skipped.
            include_international_transport (bool): Whether to add international
                aviation and navigation to the total.
            start_year (int): First year of the time series.
        """
        emissions_sectors = self.get_emissions_sectors(sectors, nodes, start_year)
        emissions_total = self.get_emissions_total(
            nodes, include_international_transport, start_year
        )
        return emissions_sectors, emissions_total

    def get_sector_share(
        self,
        sectors: list[str],
        nodes: list[str],
        include_international_transport: bool = True,
        start_year: int = UNFCCC_START_YEAR,
    ) -> pd.Series:
        """Share of the modeled sectors in the total emissions, by year.

        Args:
            sectors (list[str]): Modeled sectors, as in the model settings.
            nodes (list[str]): NUTS0 node names, those without an inventory are
                skipped.
            include_international_transport (bool): Whether to add international
                aviation and navigation to the total.
            start_year (int): First year of the time series.
        """
        emissions_sectors, emissions_total = self.get_emissions(
            sectors,
            nodes,
            include_international_transport=include_international_transport,
            start_year=start_year,
        )
        return emissions_sectors.sum() / emissions_total

    # ------ Helpers ------

    def _select(self, codes: list[str], nodes: list[str]) -> pd.DataFrame:
        """The emissions of the given sector codes and nodes, in Gg.

        Nodes without an inventory, such as the UK since it left the EU, are
        skipped. Sector and node combinations that are not reported are NaN.
        """
        if len(set(codes)) != len(codes):
            raise ValueError(f"The sector codes {codes} hold duplicates.")
        reported_codes = self.data.index.get_level_values(0)
        missing = [code for code in codes if code not in reported_codes]
        if missing:
            raise ValueError(
                f"The inventory does not report the sector codes {missing}."
            )
        reported_nodes = self.data.index.get_level_values(1)
        common_nodes = [node for node in nodes if node in reported_nodes]
        if not common_nodes:
            raise ValueError(f"The inventory reports none of the nodes {nodes}.")
        index = pd.MultiIndex.from_product(
            [codes, common_nodes], names=self.data.index.names
        )
        return self.data.reindex(index)


class EEAGreenhouseGasInventoryAllGHG(EEAGreenhouseGasInventory):
    """All greenhouse gas emissions in CO2 equivalents, as reported to the UNFCCC."""

    name = "eea_ghg_inventory_all_ghg"

    POLLUTANT = "All greenhouse gases - (CO2 equivalent)"
    UNIT = "Gg CO2 equivalent"

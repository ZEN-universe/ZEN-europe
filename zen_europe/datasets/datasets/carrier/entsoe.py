from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from entsoe import EntsoeRawClient
from entsoe.exceptions import (
    InvalidBusinessParameterError,
    InvalidPSRTypeError,
    NoMatchingDataError,
)
from entsoe.mappings import NEIGHBOURS as _SUBZONE_NEIGHBOURS
from entsoe.parsers import parse_crossborder_flows, parse_generation, parse_loads
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.settings import Settings

logger = logging.getLogger(__name__)

# This dataset queries the ENTSO-E Transparency Platform via the entsoe-py
# package (EntsoeRawClient for HTTP + entsoe.parsers for XML parsing), which
# is already a transitive dependency and handles the schema's edge cases
# (sparse/repeated positions, resolution mixes, retries) more robustly than a
# hand-rolled parser would. This module supplies: the country universe to
# iterate, node-name translation (EL/UK -> ENTSO-E's GR/GB), country-level
# folding of the bidding-zone adjacency table (for NTC edge selection), and
# disk caching / unit conversion on top of the raw per-country queries.

_API_KEY_ENV_VAR = "ENTSOE_API_KEY"

# Countries queried by default (the "full ENTSO-E universe" of mappable
# countries); callers subset the result to whatever nodes/edges they need.
# Keyed using the country code used elsewhere in ZEN-europe (Greece = "EL"
# and the United Kingdom = "UK", matching ENTSO-E's own "GR"/"GB").
_NODES: list[str] = [
    "AL",
    "AT",
    "BA",
    "BE",
    "BG",
    "BY",
    "CH",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "EL",
    "ES",
    "FI",
    "FR",
    "GE",
    "HR",
    "HU",
    "IE",
    "IS",
    "IT",
    "LT",
    "LU",
    "LV",
    "MD",
    "ME",
    "MK",
    "MT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "RS",
    "RU",
    "SE",
    "SI",
    "SK",
    "TR",
    "UA",
    "UK",
    "XK",
]
_NODE_TO_ENTSOE_CODE: dict[str, str] = {"EL": "GR", "UK": "GB"}


def _entsoe_code(node: str) -> str:
    return _NODE_TO_ENTSOE_CODE.get(node, node)


# Bidding-zone -> country-node folding for the NEIGHBOURS adjacency table
# (entsoe-py doesn't provide this, since several countries report more than
# one bidding zone).
_SUBZONE_TO_NODE: dict[str, str] = {
    "DE_AT_LU": "DE",
    "DE_LU": "DE",
    "GB": "UK",
    "NIE": "UK",
    "GR": "EL",
    "IT_GR": "IT",
    "NO_1": "NO",
    "NO_2": "NO",
    "NO_3": "NO",
    "NO_4": "NO",
    "NO_5": "NO",
    "DK_1": "DK",
    "DK_2": "DK",
    "SE_1": "SE",
    "SE_2": "SE",
    "SE_3": "SE",
    "SE_4": "SE",
    "IT_NORD": "IT",
    "IT_NORD_AT": "IT",
    "IT_NORD_CH": "IT",
    "IT_NORD_FR": "IT",
    "IT_CNOR": "IT",
    "IT_CSUD": "IT",
    "IT_SUD": "IT",
    "IT_SARD": "IT",
    "IT_SICI": "IT",
    "IT_BRNN": "IT",
    "IT_CALA": "IT",
    "IT_FOGN": "IT",
    "IT_ROSN": "IT",
    "IE_SEM": "IE",
    "RU_KGD": "RU",
}


def _country_level_neighbours() -> dict[str, set[str]]:
    """Fold entsoe-py's bidding-zone adjacency table down to one entry per
    country node, dropping self-loops introduced by countries with several
    zones (DE, DK, NO, SE, IT, IE)."""
    neighbours: dict[str, set[str]] = {}
    for zone, adjacent_zones in _SUBZONE_NEIGHBOURS.items():
        node = _SUBZONE_TO_NODE.get(zone, zone)
        for adjacent_zone in adjacent_zones:
            adjacent_node = _SUBZONE_TO_NODE.get(adjacent_zone, adjacent_zone)
            if adjacent_node == node:
                continue
            neighbours.setdefault(node, set()).add(adjacent_node)
            neighbours.setdefault(adjacent_node, set()).add(node)
    return neighbours


_NEIGHBOURS = _country_level_neighbours()


# Errors that mean "this particular country/query has no data" rather than a
# transient failure; safe to log and skip.
_SKIP_ERRORS = (NoMatchingDataError, InvalidPSRTypeError, InvalidBusinessParameterError)


class ENTSOE(Dataset[pd.DataFrame]):
    """ENTSO-E Transparency Platform dataset class.

    Queries electricity demand, generation, installed capacity, net transfer
    capacity, and historic nuclear capacity factors from the ENTSO-E
    Transparency Platform (via entsoe-py), per country, and caches results
    under ``source_path / "02-carrier" / "entsoe"``.

    Requires an API security token in the ``ENTSOE_API_KEY`` environment
    variable (generate one at https://transparency.entsoe.eu/ under "My
    Account" -> "Web API Access").
    """

    name = "entsoe"

    def __init__(
        self,
        settings: Settings,
        set_nodes: list[str],
        source_path: Path | str | None = None,
    ):
        self.settings = settings
        self.set_nodes = set_nodes
        self._client: EntsoeRawClient | None = None
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="ENTSO-E Transparency Platform",
            author=["ENTSO-E"],
            publication="ENTSO-E Transparency Platform",
            publication_year=datetime.now().year,
            url="https://transparency.entsoe.eu/",
            note=(
                "Queried via the entsoe-py package against the ENTSO-E "
                "Transparency Platform RESTful API; requires an API "
                f"security token in the {_API_KEY_ENV_VAR} environment variable."
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()  # placeholder; actual data is queried on demand

    # -------- entsoe-py client ------------------

    @property
    def _entsoe_client(self) -> EntsoeRawClient:
        if self._client is None:
            api_key = os.environ.get(_API_KEY_ENV_VAR)
            if not api_key:
                raise RuntimeError(
                    f"ENTSO-E API key not found. Set the {_API_KEY_ENV_VAR} "
                    "environment variable to a security token generated at "
                    "https://transparency.entsoe.eu/ (My Account -> Web API "
                    "Access).\nThen, add the token to your environment variables and "
                    "restart the Python process.\nYou will not need the token if you "
                    "have already have a cached dataset."
                )
            self._client = EntsoeRawClient(api_key=api_key)
        return self._client

    # -------- disk cache ------------------

    def _cache_paths(self, name: str) -> tuple[Path, Path]:
        if self.source_path is None:
            raise ValueError("source_path must be set to cache ENTSO-E data.")
        base = Path(self.source_path) / "02-carrier" / "entsoe" / name
        return base.with_suffix(".feather"), base.with_suffix(".json")

    def _cached_query(self, name, query):
        """Return the cached result for `name`, querying and caching it on
        first use. ENTSO-E queries loop over every country and are slow, so
        results are persisted as feather files with a small json sidecar
        recording how to restore the original index/columns."""
        data_path, meta_path = self._cache_paths(name)

        overwrite = self.settings.cache.overwrite_entsoe
        if data_path.exists() and meta_path.exists() and not overwrite:
            logger.info(f"Loading cached ENTSO-E data for '{name}' from {data_path}")
            frame = pd.read_feather(data_path)
            meta = json.loads(meta_path.read_text())
            frame = frame.set_index(list(frame.columns[: meta["n_index_levels"]]))
            if meta["columns_are_int"]:
                frame.columns = frame.columns.astype(int)
            return frame.squeeze("columns") if meta["is_series"] else frame

        logger.info(f"Querying ENTSO-E for '{name}' (this may take a while)...")
        data = query()

        is_series = isinstance(data, pd.Series)
        columns_are_int = not is_series and all(
            isinstance(c, int) for c in data.columns
        )
        reset = data.reset_index()
        reset.columns = reset.columns.astype(str)

        data_path.parent.mkdir(parents=True, exist_ok=True)
        reset.to_feather(data_path)
        meta_path.write_text(
            json.dumps(
                {
                    "n_index_levels": data.index.nlevels,
                    "is_series": is_series,
                    "columns_are_int": columns_are_int,
                }
            )
        )
        return data

    # -------- outward-facing accessors ------------------

    def get_demand(self) -> pd.DataFrame:
        """Hourly electricity demand [GW] per country, for the configured
        time-series year, indexed by hour of year."""
        demand = self._cached_query("demand", self._query_demand)
        demand = demand.where(demand != 0)
        demand = demand.interpolate().fillna(0)
        demand = demand / 1000  # MW -> GW
        demand = demand.reset_index(drop=True)
        demand.index.name = "time"
        return demand

    def get_generation(self, psr_type: str, year: int | None = None) -> pd.DataFrame:
        """Hourly actual generation [GW] per country for a given production
        type (see `entsoe.mappings.PSRTYPE_MAPPINGS`), indexed by hour of year.

        Args:
            psr_type: ENTSO-E production-type code, e.g. "B14" for nuclear.
            year: Year to query; defaults to `settings.time.reference_year`.
        """
        year = year if year is not None else self.settings.time.reference_year
        generation = self._cached_query(
            f"generation_{psr_type}_{year}",
            lambda: self._query_generation(psr_type, year),
        )
        generation = generation.astype(float).interpolate()
        generation = generation / 1000  # MW -> GW
        generation = generation.reset_index(drop=True)
        generation.index.name = "time"
        return generation

    def get_capacity_existing(
        self, psr_type: str, year: int | None = None
    ) -> pd.Series:
        """Year-ahead installed generation capacity [GW] per country for a
        given production type, indexed by (node, year_construction).

        Args:
            psr_type: ENTSO-E production-type code, e.g. "B14" for nuclear.
            year: Year to query; defaults to `settings.time.reference_year`.
        """
        year = year if year is not None else self.settings.time.reference_year
        capacity = self._cached_query(
            f"capacity_{psr_type}_{year}",
            lambda: self._query_capacity_existing(psr_type, year),
        )
        capacity = capacity.dropna()
        capacity = capacity[capacity != 0]
        return capacity / 1000  # MW -> GW

    def get_transmission_capacity(self) -> pd.DataFrame:
        """Net transfer capacity [GW] between neighbouring countries,
        indexed by (edge, year_construction), where edge is "NODE_FROM-NODE_TO".

        Countries that share a merged bidding zone (e.g. DE and LU) have no
        direct NTC series and are not included; callers modeling such edges
        need to substitute their own assumption.
        """
        year = self.settings.time.reference_year - 1
        monthly = self.settings.data_source.use_monthly_entsoe_ntc
        cache_name = (
            f"transmission_capacity_{'monthly' if monthly else 'yearly'}_{year}"
        )
        capacity = self._cached_query(
            cache_name, lambda: self._query_transmission_capacity(year, monthly)
        )
        capacity = capacity.fillna(0).sort_index() / 1000  # MW -> GW
        capacity.index = pd.MultiIndex.from_arrays(
            [capacity.index, [year] * len(capacity)],
            names=["edge", "year_construction"],
        )
        return capacity.rename("capacity_existing").to_frame()

    # -------- per-country query loops ------------------

    def _query_demand(self) -> pd.DataFrame:
        year = self.settings.time.year_time_series
        start, end = self._year_bounds(year)
        demand = pd.DataFrame(
            index=pd.date_range(start, end, freq="1h", inclusive="left")
        )
        for idx, node in enumerate(self.set_nodes):
            logger.info(
                f"Querying ENTSO-E demand for {node} - {idx + 1}/{len(self.set_nodes)}"
            )
            area = _entsoe_code(node)
            try:
                xml_text = self._entsoe_client.query_load(area, start=start, end=end)
                frame = parse_loads(xml_text, process_type="A16")
            except _SKIP_ERRORS:
                try:
                    xml_text = self._entsoe_client.query_load_forecast(
                        area, start=start, end=end, process_type="A01"
                    )
                    frame = parse_loads(xml_text, process_type="A01")
                    logger.info(f"Using forecasted load for {node}")
                except _SKIP_ERRORS:
                    logger.info(f"No demand data found for {node}")
                    continue
                except requests.RequestException as exc:
                    logger.warning(f"Load forecast query failed for {node}: {exc}")
                    continue
            except requests.RequestException as exc:
                logger.warning(f"Load query failed for {node}: {exc}")
                continue
            series = frame.iloc[:, 0]
            if series.empty:
                continue
            demand[node] = series.resample("1h").mean()
        demand.index.name = "time"
        return demand

    def _query_generation(self, psr_type: str, year: int) -> pd.DataFrame:
        start, end = self._year_bounds(year)
        generation = pd.DataFrame(
            index=pd.date_range(start, end, freq="1h", inclusive="left")
        )
        for idx, node in enumerate(self.set_nodes):
            logger.info(
                f"Querying ENTSO-E generation for {node} of type {psr_type}"
                f"- {idx + 1}/{len(self.set_nodes)}"
            )
            area = _entsoe_code(node)
            try:
                xml_text = self._entsoe_client.query_generation(
                    area, start=start, end=end, psr_type=psr_type
                )
            except _SKIP_ERRORS:
                logger.info(f"No generation data found for {node} ({psr_type})")
                continue
            except requests.RequestException as exc:
                logger.warning(f"Generation query failed for {node}: {exc}")
                continue
            series = parse_generation(xml_text, nett=True)
            if isinstance(series, pd.DataFrame):
                # multiple production sub-series can remain if netting wasn't
                # applicable; sum whatever generation-like columns are left
                series = series.sum(axis=1)
            if series.empty:
                continue
            generation[node] = series.resample("1h").mean()
        generation.index.name = "time"
        return generation

    def _query_capacity_existing(self, psr_type: str, year: int) -> pd.Series:
        start, end = self._year_bounds(year)
        capacity: dict[str, float] = {}
        for idx, node in enumerate(self.set_nodes):
            logger.info(
                f"Querying ENTSO-E installed capacity for {node} of type {psr_type}"
                f"- {idx + 1}/{len(self.set_nodes)}"
            )
            area = _entsoe_code(node)
            try:
                xml_text = self._entsoe_client.query_installed_generation_capacity(
                    area, start=start, end=end, psr_type=psr_type
                )
            except _SKIP_ERRORS:
                logger.info(f"No installed capacity data found for {node} ({psr_type})")
                continue
            except requests.RequestException as exc:
                logger.warning(f"Installed capacity query failed for {node}: {exc}")
                continue
            series = parse_generation(xml_text, nett=True)
            if isinstance(series, pd.DataFrame):
                series = series.sum(axis=1)
            if series.empty:
                continue
            series.index = series.index.year
            series = series.groupby(series.index).sum()
            capacity[node] = (
                float(series.loc[year])
                if year in series.index
                else float(series.iloc[-1])
            )
        index = pd.MultiIndex.from_tuples(
            [(node, year) for node in capacity], names=["node", "year_construction"]
        )
        return pd.Series(
            [capacity[node] for node, _ in index], index=index, name="capacity_existing"
        )

    def _query_transmission_capacity(self, year: int, monthly: bool) -> pd.Series:
        start, end = self._year_bounds(year)
        edges = sorted(
            (node_from, node_to)
            for node_from, adjacent in _NEIGHBOURS.items()
            for node_to in adjacent
            if node_from in _NODES and node_to in _NODES
        )
        capacity: dict[str, float] = {}
        for idx, (node_from, node_to) in enumerate(edges):
            logger.info(
                f"Querying ENTSO-E transmission capacity from"
                f"{node_from} to {node_to} - {idx + 1}/{len(edges)}"
            )
            capacity[f"{node_from}-{node_to}"] = self._query_ntc(
                node_from, node_to, start, end, monthly
            )
        return pd.Series(capacity, dtype=float)

    def _query_ntc(
        self,
        node_from: str,
        node_to: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        monthly: bool,
    ) -> float:
        area_from = _entsoe_code(node_from)
        area_to = _entsoe_code(node_to)
        try:
            if monthly:
                xml_text = self._entsoe_client.query_net_transfer_capacity_monthahead(
                    country_code_from=area_from,
                    country_code_to=area_to,
                    start=start,
                    end=end,
                )
            else:
                xml_text = self._entsoe_client.query_net_transfer_capacity_yearahead(
                    country_code_from=area_from,
                    country_code_to=area_to,
                    start=start,
                    end=end,
                )
        except _SKIP_ERRORS:
            logger.info(
                f"No transmission capacity data found" f"from {node_from} to {node_to}"
            )
            return float("nan")
        except requests.RequestException as exc:
            logger.warning(
                f"Transmission capacity query failed"
                f"from {node_from} to {node_to}: {exc}"
            )
            return float("nan")
        series = parse_crossborder_flows(xml_text)
        if series.empty:
            return float("nan")
        return float(series.max())

    @staticmethod
    def _year_bounds(year: int) -> tuple[pd.Timestamp, pd.Timestamp]:
        start = pd.Timestamp(year=year, month=1, day=1, tz="Europe/Brussels")
        end = pd.Timestamp(year=year + 1, month=1, day=1, tz="Europe/Brussels")
        return start, end

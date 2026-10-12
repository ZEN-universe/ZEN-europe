from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.settings import Settings

from zen_europe.utils.utils import (
    convert_country_names,
    instance_cache,
    linearly_fill_missing_years,
)

logger = logging.getLogger(__name__)

# UNECE publishes its transport statistics through a PXWeb 2015 instance. The
# API mirrors the folder structure of the web front-end, so the road-fleet
# tables live under STAT/40-TRTRANS/03-TRRoadFleet.
_UNECE_API_BASE = (
    "https://w3.unece.org/PXWeb2015/api/v1/en/STAT/40-TRTRANS/03-TRRoadFleet"
)
_UNECE_TABLES = {
    # New road vehicle registrations by vehicle category and fuel type
    "registrations": "08_en_TRRoadNewVehF_r.px",
    # Road vehicle fleet at 31 December by vehicle category and fuel type
    "fleet": "03_en_TRRoadFuelFlt_r.px",
}
# The PXWeb instance rejects a request for a whole table (all five vehicle
# categories at once) as too large, so it is queried one vehicle category at a
# time; it also rate-limits bursts of requests, hence the delay between
# requests and the retry-with-backoff on HTTP 429.
_REQUEST_DELAY = 3.0
_MAX_RETRIES = 5
_RETRY_BACKOFF = 10.0

_INDEX_NAMES = ["vehicle_type", "fuel_type", "node"]

# The vehicle categories are named differently in the two tables.
_PASSENGER_CARS = {"registrations": "New passenger cars", "fleet": "Passenger cars"}
_LORRIES = {
    "registrations": "New lorries (vehicle wt over 3500 kg)",
    "fleet": "Lorries (vehicle wt over 3500 kg)",
}

# Fuel types are reported both as aggregates ("Petrol") and as mutually
# exclusive sub-categories ("Petrol (excluding hybrids)", "Hybrid
# electric-petrol", ...). Not every country reports the split, so the
# conventional-drivetrain figure is taken as the minimum of the aggregate and
# the "excluding hybrids" row: where the split is reported the latter is
# smaller, where it is not the former is the only value available.
_DIESEL_INCLUDING_HYBRIDS = "Diesel"
_PETROL = ["Petrol", "Petrol (excluding hybrids)"]
_DIESEL = [_DIESEL_INCLUDING_HYBRIDS, "Diesel (excluding hybrids)"]
_HYBRID = ["Hybrid electric-petrol", "Hybrid electric-diesel"]
_PLUG_IN_HYBRID = [
    "Plug-in hybrid petrol-electric",
    "Plug-in hybrid diesel-electric",
]
# LPG and (compressed/liquefied) natural gas cars are not modelled separately
# and are counted towards the petrol cars.
_GASEOUS = ["Compressed natural gas (CNG)", "Liquefied natural gas (LNG)", "LPG"]
_ELECTRIC = "Electricity"
_HYDROGEN = "Hydrogen and fuel cells"
# Passenger-car drivetrains without a corresponding technology in the model
# (hydrogen cars among them, unlike hydrogen trucks). They are subtracted from
# the reported total, so that the total matches the sum over the modelled
# drivetrains.
_OTHER = ["Bioethanol", "Biodiesel", "Bi-fuel vehicles", _HYDROGEN]
_TOTAL = "Total"

# Names of the passenger-car technologies in zen_europe.
_PETROL_CAR = "ICE_petrol"
_DIESEL_CAR = "ICE_diesel"
_ELECTRIC_CAR = "BEV"
_HYBRID_CAR = "HEV"
_PLUG_IN_HYBRID_CAR = "PHEV"

# Names of the heavy-duty truck technologies in zen_europe. Petrol, gas and
# biofuel lorries exist but are not modelled, so unlike the passenger cars they
# are dropped rather than folded into another drivetrain.
_DIESEL_TRUCK = "HDT_diesel"
_ELECTRIC_TRUCK = "HDT_BET"
_HYDROGEN_TRUCK = "HDT_FCEV"

# UNECE reports 1048 new electric lorries in the United Kingdom in 2016, two
# orders of magnitude above the surrounding years (3 in 2015, 12 in 2017);
# Eurostat reports 8. The outlier is still in the live data, so it is corrected
# here.
_TRUCK_CORRECTIONS: dict[str, dict[tuple[str, str, int], float]] = {
    "registrations": {(_ELECTRIC_TRUCK, "UK", 2016): 8.0},
}


class UNECE(Dataset[dict[str, pd.DataFrame]]):
    """UNECE road vehicle fleet and new-registration statistics.

    Queries the UNECE transport statistics PXWeb API for the road vehicle
    fleet at 31 December and for the new road vehicle registrations, both
    broken down by vehicle category, fuel type, country and year, and caches
    the raw tables on disk.
    """

    name = "unece"

    def __init__(self, settings: Settings, source_path: Path | str | None = None):
        self.settings = settings
        self.unece_year = self.settings.time.reference_year - 1
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Road vehicle fleet at 31 December and new road vehicle "
                "registrations, by vehicle category and fuel type"
            ),
            author=["United Nations Economic Commission for Europe"],
            publication="UNECE Transport Statistics Database",
            publication_year=datetime.now().year,
            url=(
                "https://w3.unece.org/PXWeb2015/pxweb/en/STAT/STAT__40-TRTRANS"
                "__03-TRRoadFleet"
            ),
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> dict[str, pd.DataFrame]:
        return {table: self._load_raw_data(table) for table in _UNECE_TABLES}

    # -------- disk cache ------------------

    def _cache_path(self, table: str) -> Path:
        """Path to the on-disk cache file for one raw UNECE table."""
        if self.source_path is None:
            raise ValueError("source_path must be set to cache UNECE data.")
        return (
            Path(self.source_path)
            / "03-technology"
            / "capacity_existing"
            / "transport"
            / "unece"
            / f"{table}.feather"
        )

    def _cached_table(self, table: str) -> pd.DataFrame:
        """Return one full raw UNECE table, querying and caching it on first
        use.

        The unprocessed table (all vehicle categories, countries and years) is
        cached, so that changing the reference year or the set of nodes does
        not require another download.
        """
        cache_path = self._cache_path(table)

        if cache_path.exists() and not self.settings.cache.overwrite_unece:
            logger.info(f"Loading cached UNECE data for '{table}' from {cache_path}")
            data = pd.read_feather(cache_path).set_index(
                ["vehicle_type", "fuel_type", "country"]
            )
            data.columns = data.columns.astype(int)
            return data

        logger.info(f"Querying UNECE for '{table}' (this may take a while)...")
        data = self._query_table(_UNECE_TABLES[table])

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        reset = data.reset_index()
        reset.columns = reset.columns.astype(str)
        reset.to_feather(cache_path)
        return data

    # -------- API queries ------------------

    def _query_table(self, table_id: str) -> pd.DataFrame:
        """Query one full PXWeb table, one vehicle category at a time."""
        url = f"{_UNECE_API_BASE}/{table_id}"
        metadata = self._request(url).json()
        vehicle_types = next(
            variable
            for variable in metadata["variables"]
            if variable["code"] == "Type of Vehicle"
        )

        data = pd.concat(
            self._query_vehicle_type(url, vehicle_type)
            for vehicle_type in vehicle_types["values"]
        )
        data = data.unstack("Year")
        data.columns = data.columns.astype(int)
        data = data.rename_axis(
            index={
                "Type of Vehicle": "vehicle_type",
                "Fuel Type": "fuel_type",
                "Country": "country",
            }
        )
        data = data.reorder_levels(["vehicle_type", "fuel_type", "country"])
        data = data.rename(
            index=lambda value: value.removeprefix("- "), level="fuel_type"
        )
        return data.sort_index()

    def _query_vehicle_type(self, url: str, vehicle_type: str) -> pd.Series:
        """Query all fuel types, countries and years of one vehicle category,
        and return them as a series indexed by the table dimensions."""
        query = {
            "query": [
                {"code": "Fuel Type", "selection": {"filter": "all", "values": ["*"]}},
                {
                    "code": "Type of Vehicle",
                    "selection": {"filter": "item", "values": [vehicle_type]},
                },
                {"code": "Country", "selection": {"filter": "all", "values": ["*"]}},
                {"code": "Year", "selection": {"filter": "all", "values": ["*"]}},
            ],
            "response": {"format": "json-stat2"},
        }
        response = self._request(url, query=query).json()
        dimensions = response["id"]
        index = pd.MultiIndex.from_product(
            [
                list(response["dimension"][dimension]["category"]["label"].values())
                for dimension in dimensions
            ],
            names=dimensions,
        )
        return pd.Series(response["value"], index=index, dtype=float)

    def _request(self, url: str, query: dict | None = None) -> requests.Response:
        """Send a request to the UNECE API, retrying while it is rate-limited.

        A GET returns the table metadata, a POST with a query body the data.
        """
        for attempt in range(_MAX_RETRIES):
            if query is None:
                response = requests.get(url, timeout=300)
            else:
                response = requests.post(
                    url,
                    data=json.dumps(query),
                    headers={"Content-Type": "application/json"},
                    timeout=300,
                )
            if response.status_code != requests.codes.too_many_requests:
                response.raise_for_status()
                time.sleep(_REQUEST_DELAY)
                return response
            backoff = _RETRY_BACKOFF * (attempt + 1)
            logger.info(
                f"UNECE API rate-limited the request, retrying in {backoff:.0f}s"
            )
            time.sleep(backoff)
        raise RuntimeError(
            f"UNECE API kept rate-limiting the request to {url} after "
            f"{_MAX_RETRIES} attempts."
        )

    # -------- raw data ------------------

    def _load_raw_data(self, table: str) -> pd.DataFrame:
        """Return one raw UNECE table, restricted to the modelled nodes and to
        the years up to the reference year.

        Missing years within the reported range are interpolated linearly over
        the years, years after the last reported one are held constant. Both
        happen before the table is cut off at the reference year, so that a
        gap is closed with the closest reported years even if one of them lies
        beyond the cutoff.
        """
        data = self._cached_table(table)

        countries = data.index.get_level_values("country")
        nodes = convert_country_names(pd.Series(countries)).to_numpy()
        is_node = pd.notna(nodes)
        data = data[is_node].copy()
        data.index = pd.MultiIndex.from_arrays(
            [
                data.index.get_level_values("vehicle_type"),
                data.index.get_level_values("fuel_type"),
                nodes[is_node],
            ],
            names=_INDEX_NAMES,
        )

        data = data.interpolate(method="index", axis=1)
        data = data.loc[:, data.columns <= self.unece_year]
        if data.empty:
            raise ValueError(
                f"The UNECE table '{table}' has no data up to {self.unece_year}."
            )
        return data.sort_index()

    # -------- outward-facing accessors ------------------

    def get_raw_data(self, table: str) -> pd.DataFrame:
        """Return one raw UNECE table ('registrations' or 'fleet'), indexed by
        vehicle type, fuel type and node, with the years as columns."""
        if table not in _UNECE_TABLES:
            raise ValueError(
                f"Unknown UNECE table '{table}', expected one of "
                f"{sorted(_UNECE_TABLES)}."
            )
        return self.data[table]

    @instance_cache
    def get_registrations(self, hybrids_separate: bool = False) -> pd.DataFrame:
        """New passenger car registrations per technology, node and year.

        Args:
            hybrids_separate: Whether hybrids (HEV) and plug-in hybrids (PHEV)
                are modelled as separate technologies. If not, they are counted
                towards the petrol cars.

        Returns:
            The registrations indexed by technology and node, with the years as
            columns.
        """
        aggregated, total = self.get_passenger_vehicles(
            "registrations", hybrids_separate
        )
        return self._allocate_unassigned_vehicles(aggregated, total, hybrids_separate)

    @instance_cache
    def get_fleet(self, hybrids_separate: bool = False) -> pd.DataFrame:
        """Passenger car fleet per technology, node and year.

        Args:
            hybrids_separate: Whether hybrids (HEV) and plug-in hybrids (PHEV)
                are modelled as separate technologies. If not, they are counted
                towards the petrol cars.

        Returns:
            The fleet indexed by technology and node, with the years as
            columns.
        """
        aggregated, total = self.get_passenger_vehicles("fleet", hybrids_separate)
        return self._allocate_unassigned_vehicles(aggregated, total, hybrids_separate)

    @instance_cache
    def get_total_fleet(self, hybrids_separate: bool = False) -> pd.DataFrame:
        """Total passenger car fleet per node and year, excluding the
        drivetrains that are not modelled.

        Args:
            hybrids_separate: Whether hybrids (HEV) and plug-in hybrids (PHEV)
                are modelled as separate technologies.
        """
        aggregated, total = self.get_passenger_vehicles("fleet", hybrids_separate)
        return self._reconcile_total(aggregated, total)

    @instance_cache
    def get_truck_registrations(self) -> pd.DataFrame:
        """New heavy-duty truck registrations per technology, node and year.

        Returns:
            The registrations indexed by technology and node, with the years as
            columns.
        """
        return self.get_trucks("registrations")[0]

    @instance_cache
    def get_truck_fleet(self) -> pd.DataFrame:
        """Heavy-duty truck fleet per technology, node and year.

        Returns:
            The fleet indexed by technology and node, with the years as
            columns.
        """
        return self.get_trucks("fleet")[0]

    @instance_cache
    def get_total_truck_fleet(self) -> pd.DataFrame:
        """Total heavy-duty truck fleet per node and year."""
        return self._reconcile_total(*self.get_trucks("fleet"))

    def get_passenger_vehicles(
        self, table: str, hybrids_separate: bool = False
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Aggregate the passenger cars of one UNECE table into the
        drivetrains modelled in zen_europe.

        Args:
            table: Either 'registrations' or 'fleet'.
            hybrids_separate: Whether hybrids (HEV) and plug-in hybrids (PHEV)
                are modelled as separate technologies. If not, they are counted
                towards the petrol cars.

        Returns:
            A tuple of the vehicles per technology and node, and of the
            reported total per node (both with the years as columns).
        """
        data = self.get_raw_data(table).loc[_PASSENGER_CARS[table]]

        petrol = data.loc[_PETROL].groupby(level=1).min()
        diesel = data.loc[_DIESEL].groupby(level=1).min()
        hybrid = data.loc[_HYBRID].groupby(level=1).sum()
        plug_in_hybrid = data.loc[_PLUG_IN_HYBRID].groupby(level=1).sum()
        electric = data.loc[_ELECTRIC]
        # LPG/CNG/LNG cars are counted towards the petrol cars
        petrol = petrol + data.loc[_GASEOUS].groupby(level=1).sum()

        if hybrids_separate:
            aggregated = pd.concat(
                [petrol, diesel, hybrid, plug_in_hybrid, electric],
                keys=[
                    _PETROL_CAR,
                    _DIESEL_CAR,
                    _HYBRID_CAR,
                    _PLUG_IN_HYBRID_CAR,
                    _ELECTRIC_CAR,
                ],
            )
        else:
            petrol = petrol + hybrid + plug_in_hybrid
            aggregated = pd.concat(
                [petrol, diesel, electric],
                keys=[_PETROL_CAR, _DIESEL_CAR, _ELECTRIC_CAR],
            )
        # the drivetrains that are not modelled are excluded from the total
        total = data.loc[_TOTAL] - data.loc[_OTHER].groupby(level=1).sum()

        aggregated = linearly_fill_missing_years(aggregated)
        total = linearly_fill_missing_years(total)
        aggregated.index.names = ["technology", "node"]
        total.index.name = "node"
        return aggregated, total

    def get_trucks(self, table: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Aggregate the heavy-duty trucks (lorries over 3500 kg) of one UNECE
        table into the drivetrains modelled in zen_europe.

        Args:
            table: Either 'registrations' or 'fleet'.

        Returns:
            A tuple of the trucks per technology and node, and of the reported
            total per node (both with the years as columns).
        """
        data = self.get_raw_data(table).loc[_LORRIES[table]]
        data = data.loc[:, data.notna().any(axis=0)]

        total = data.loc[_TOTAL]
        diesel = (
            pd.concat([total, data.loc[_DIESEL_INCLUDING_HYBRIDS]])
            .groupby(level=0)
            .min()
        )
        electric = data.loc[_ELECTRIC].fillna(0)
        hydrogen = data.loc[_HYDROGEN].fillna(0)

        aggregated = pd.concat(
            [diesel, electric, hydrogen],
            keys=[_DIESEL_TRUCK, _ELECTRIC_TRUCK, _HYDROGEN_TRUCK],
        )
        aggregated.index.names = ["technology", "node"]
        total.index.name = "node"

        # correct the outlier in the UK electric-truck registrations in 2016
        for (technology, node, year), value in _TRUCK_CORRECTIONS.get(
            table, {}
        ).items():
            if (technology, node) in aggregated.index and year in aggregated:
                aggregated.loc[(technology, node), year] = value

        aggregated = aggregated.bfill(axis=1)
        total = total.bfill(axis=1)
        return aggregated.sort_index(), total.sort_index()

    # -------- helpers ------------------

    @staticmethod
    def _reconcile_total(aggregated: pd.DataFrame, total: pd.DataFrame) -> pd.DataFrame:
        """Return the total per node, raised to the sum over the technologies
        wherever the reported total falls short of it."""
        return (
            pd.concat([total, aggregated.groupby(level=1).sum()]).groupby(level=0).max()
        )

    def _allocate_unassigned_vehicles(
        self,
        aggregated: pd.DataFrame,
        total: pd.DataFrame,
        hybrids_separate: bool,
    ) -> pd.DataFrame:
        """Distribute the vehicles that the fuel-type breakdown does not
        account for over the modelled technologies.

        Some countries (e.g. CZ, SK) report a total but no, or an incomplete,
        breakdown by fuel type. The difference between the total and the sum
        over the modelled drivetrains is assumed to be petrol cars, except for
        Germany, whose breakdown is missing the hybrids that Eurostat does
        report; there the difference is split evenly between hybrids and
        plug-in hybrids whenever those are modelled.
        """
        total = self._reconcile_total(aggregated, total)
        delta = total - aggregated.groupby(level=1).sum()

        for node in delta.index:
            if node == "DE" and hybrids_separate:
                aggregated.loc[_HYBRID_CAR, node] += delta.loc[node] / 2
                aggregated.loc[_PLUG_IN_HYBRID_CAR, node] += delta.loc[node] / 2
            else:
                aggregated.loc[_PETROL_CAR, node] = aggregated.loc[
                    _PETROL_CAR, node
                ].add(delta.loc[node], fill_value=0)
        return aggregated.sort_index()

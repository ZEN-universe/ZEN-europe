from __future__ import annotations

import hashlib
import json
import logging
import multiprocessing as mp
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Union, cast

import eurostat as es
import pandas as pd
import requests
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData
from zen_creator.utils.settings import Settings

from zen_europe.utils.constants import Constants
from zen_europe.utils.utils import instance_cache

logger = logging.getLogger(__name__)

# siec (Standard International Energy Product Classification) codes for the
# power-plant/carrier types covered by the fleet-efficiency calculation.
_EFFICIENCY_SIEC = {
    "C0220": "lignite",
    "C0129": "hard_coal",
    "N900H": "uranium",
    "W6100_6220": "waste",
    "G3000": "natural_gas",
    "O4000XBIO": "oil",
    "R5110-5150_W6000RI": "biomass",
}
_EFFICIENCY_NRG_BAL = {"TI_EHG_MAPE_E": "input", "GEP_MAPE": "output"}
_EFFICIENCY_TECHNOLOGY_NAMES = {
    "lignite": "lignite_coal_plant",
    "hard_coal": "hard_coal_plant",
    "uranium": "nuclear",
    "waste": "waste_plant",
    "natural_gas": "natural_gas_turbine",
    "oil": "oil_plant",
    "biomass": "biomass_plant",
}


_HEAT_TECHNOLOGY_NAMES = {
    "Solid fossil fuels": "hard_coal_boiler",
    "Peat and peat products": "hard_coal_boiler",
    "Oil and petroleum products": "oil_boiler",
    "Natural gas": "natural_gas_boiler",
    "Primary solid biofuels": "biomass_boiler",
    "Biogases": "biomass_boiler",
    "Electricity": "electrode_boiler",
    "Ambient heat": "heat_pump",
    "Heat": "heat",
    "Non-renewable waste": "waste_boiler",
    "Manufactured gases": "natural_gas_boiler",
    "Nuclear heat": "hard_coal_boiler",
}
_HEAT_TECHNOLOGY_NAMES_DH = {
    "Solid fossil fuels": "hard_coal_boiler_DH",
    "Peat and peat products": "hard_coal_boiler_DH",
    "Oil and petroleum products": "oil_boiler_DH",
    "Natural gas": "natural_gas_boiler_DH",
    "Primary solid biofuels": "biomass_boiler_DH",
    "Biogases": "biomass_boiler_DH",
    "Electricity": "electrode_boiler_DH",
    "Ambient heat": "heat_pump_DH",
    "Heat": "heat",
    "Non-renewable waste": "waste_boiler_DH",
    "Manufactured gases": "natural_gas_boiler_DH",
    "Nuclear heat": "hard_coal_boiler_DH",
}
_HEAT_HOUSEHOLD_SIEC_TOTAL = {"TOTAL": "Total"}

_HEAT_HOUSEHOLD_SIEC = {
    "G3000": "natural_gas_boiler",
    "O4000": "oil_boiler",  # Oil and petroleum products (larger category)
    "RA600": "heat_pump",  # Ambient heat (heat pumps)
    "R5110-5150_W6000RI": "biomass_boiler",  # Primary solid biofuels
    "R5300": "biomass_boiler",  # Biogases
    "E7000": "electricity",  # Electricity
    "H8000": "heat",  # Heat
}

_HEAT_HOUSEHOLD_NRG_BAL = {
    "FC_OTH_HH_E_SH": "space_heating",
    "FC_OTH_HH_E_WH": "water_heating",
}
_HEAT_HOUSEHOLD_DATASET = "nrg_d_hhq"
_HEAT_HOUSEHOLD_UNIT = "TJ"

_HEAT_DH_SIEC = {
    "C0000X0350-0370": "hard_coal_boiler_DH",  # Solid fossil fuels
    "P1000": "hard_coal_boiler_DH",  # Peat and peat products
    "O4000XBIO": "oil_boiler_DH",  # Oil and petroleum products
    "G3000": "natural_gas_boiler_DH",  # Natural gas
    "R5110-5150_W6000RI": "biomass_boiler_DH",  # Primary solid biofuels
    "R5300": "biomass_boiler_DH",  # Biogases
    "E7000": "electricity_DH",  # Electricity
    "RA600": "heat_pump_DH",  # Ambient heat
    "W6100_6220": "waste_boiler_DH",  # Non-renewable waste
    "C0350-0370": "natural_gas_boiler_DH",  # Manufactured gases
    "N900H": "hard_coal_boiler_DH",  # Nuclear heat
}

_HEAT_DH_NRG_BAL = {
    "GHP": "Gross heat production",
}

_COAL_SIEC = {"C0220": "lignite", "C0129": "hard_coal"}
_COAL_NRG_BAL = {
    # "TI_EHG_E": "Transformation Input",
    # "FC_OTH_HH_E": "Final consumption - other sectors - energy use households",
    # "FC_OTH_CP_E": "Final consumption - other sectors - energy use commercial",
    "IMP": "Imports",
    "PPRD": "Production",
}

_NATURAL_GAS_SIEC = {"G3000": "natural_gas"}
_NATURAL_GAS_NRG_BAL = {"PPRD": "Production"}

_BIOMASS_SIEC = {"R5110-5150_W6000RI": "biomass", "R5300": "biogas"}
_BIOMASS_NRG_BAL = {
    "IMP": "Imports",
    "PPRD": "Production",
}

_OIL_SIEC = {"O4000XBIO": "oil", "S2000": "oil shale"}
_OIL_NRG_BAL = {
    "IMP": "Imports",
    "PPRD": "Production",
}

_WASTE_SIEC = {"W6100_6220": "waste"}
_WASTE_NRG_BAL = {
    "IMP": "Imports",
    "PPRD": "Production",
}
_WASTE_INDUSTRY_NRG_BAL = {
    "FC_IND_E": "Final consumption - industry sector - energy use",
}

_NAPHTHA_SIEC = {"O4640": "naphtha"}
_NAPHTHA_NRG_BAL = {"TO": "Transformation Output"}

_KEROSENE_SIEC = {"O4661XR5230B": "kerosene"}
_KEROSENE_NRG_BAL = {
    "INTAVI": "International Aviation",
    "FC_TRA_DAVI_E": "Domestic aviation",
}

_SHIPPING_FUEL_SIEC = {"O4680": "Fuel oil", "O4671XR5220B": "Gas diesel oil"}
_SHIPPING_FUEL_NRG_BAL = {
    "INTMARB": "International Maritime Bunkers",
    "FC_TRA_DNAVI_E": "Domestic navigation",
}

# Eurostat data-availability cutoffs (intrinsic to the source database, not
# model settings).
_EUROSTAT_START_YEAR = 1990
_LAST_EUROSTAT_YEAR_UK = 2019
_MAX_QUERY_WORKERS = 4
_QUERY_ATTEMPTS = 3

# ilc_lvho01: population by degree of urbanization ("deg_urb").
_URBANIZATION_DATASET = "ilc_lvho01"
_URBANIZATION_RISK_OF_POVERTY = {"TOTAL": "total"}
_URBANIZATION_TYPE_OF_BUILDING = {"TOTAL": "total"}
_URBANIZATION_DEGREE = {
    "DEG1": "cities",
    "DEG2": "towns_and_suburbs",
    "DEG3": "rural",
}


class Eurostat(Dataset[pd.DataFrame]):
    """Dataset class for Eurostat energy-balance and vehicle-fleet data.

    This class implements the specific behavior for the Eurostat dataset.
    """

    name = "eurostat"

    def __init__(self, settings: Settings, source_path: Path | str | None = None):
        self.settings = settings
        self.source_path = Path(source_path) if source_path is not None else None

        last_eurostat_year = self._get_latest_year("nrg_bal_c")
        eurostat_year = min(last_eurostat_year, self.settings.time.reference_year - 1)
        if self.settings.time.reference_year - 1 > last_eurostat_year:
            logging.info(
                f"Reference year {self.settings.time.reference_year} is after the last"
                f"available Eurostat year {last_eurostat_year}. "
                f"Using {eurostat_year} instead."
            )
        self.eurostat_year = eurostat_year
        self.eurostat_time_series_year = min(
            eurostat_year, self.settings.time.time_series_year
        )

        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Eurostat energy balances",
            author=["Eurostat"],
            publication="Eurostat",
            publication_year=datetime.now().year,
            url="https://ec.europa.eu/eurostat/databrowser/view/nrg_bal_c/default/table?lang=en",
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()  # placeholder, actual data is queried on demand

    # -------- disk cache ------------------

    def _get_latest_year(self, dataset: str) -> int:
        """Return the latest year reported for a Eurostat dataset.

        The cached value avoids a live metadata request during an otherwise cached
        model run. A requested overwrite deliberately refreshes the value and lets
        any Eurostat error propagate to the caller.

        Args:
            dataset: Eurostat dataset identifier.

        Returns:
            Latest year reported by Eurostat.

        Raises:
            ValueError: If no source path is configured or Eurostat returns invalid
                metadata.
        """
        if self.source_path is None:
            raise ValueError("source_path must be set to cache Eurostat metadata.")

        cache_path = (
            self.source_path / "02-carrier" / "eurostat" / f"{dataset}_data_end.json"
        )
        if cache_path.exists() and not self.settings.cache.overwrite_eurostat:
            logger.info(f"Loading cached Eurostat metadata from {cache_path}")
            cached = json.loads(cache_path.read_text())
            if not isinstance(cached, int):
                raise ValueError(
                    f"Eurostat metadata cache '{cache_path}' must contain one year."
                )
            return cached

        metadata = es.get_toc_df(agency="EUROSTAT", dataset=dataset)
        if metadata.empty or "data end" not in metadata:
            raise ValueError(
                f"Eurostat returned no usable metadata for dataset '{dataset}'."
            )
        years = pd.to_numeric(metadata["data end"], errors="coerce").dropna()
        if len(years) != 1:
            raise ValueError(
                f"Eurostat returned {len(years)} latest-year values for dataset "
                f"'{dataset}'; expected exactly one."
            )

        latest_year = int(years.iloc[0])
        self._write_json_atomic(cache_path, latest_year)
        return latest_year

    def _cache_paths(self, name: str) -> tuple[Path, Path]:
        """Paths to the on-disk cache file and its metadata sidecar."""
        if self.source_path is None:
            raise ValueError("source_path must be set to cache Eurostat data.")
        base = Path(self.source_path) / "02-carrier" / "eurostat" / name
        return base.with_suffix(".feather"), base.with_suffix(".json")

    def _get_par_values(self, dataset: str, par: str) -> list[str]:
        """Return the cached allowed values of a Eurostat dataset parameter
        (e.g. "geo", "siec", "nrg_bal"), querying and caching them on first
        use."""
        if self.source_path is None:
            raise ValueError("source_path must be set to cache Eurostat data.")
        path = (
            Path(self.source_path) / "02-carrier" / "eurostat" / f"{dataset}_{par}.json"
        )
        if path.exists() and not self.settings.cache.overwrite_eurostat:
            return json.loads(path.read_text())

        values = es.get_par_values(dataset, par)
        if not values:
            raise ValueError(
                f"No values found for Eurostat dataset '{dataset}' parameter '{par}'\n"
                "Check that the eurostat server is available and "
                "that the dataset/parameter names are correct."
            )
        self._write_json_atomic(path, values)
        return values

    def _cached_query(
        self, name: str, query: Callable[[], Union[pd.Series, pd.DataFrame]]
    ) -> Union[pd.Series, pd.DataFrame]:
        """Return the cached Eurostat result for `name`, querying and
        caching it on first use.

        Extracting data from Eurostat is slow, so results are persisted
        under ``source_path/02-carrier/eurostat/<name>.feather``. Feather
        requires string column names and a flat, default index, so the
        result's index/columns are normalized before writing and restored
        (using a small json metadata sidecar) after reading.
        """
        data_path, meta_path = self._cache_paths(name)

        overwrite = self.settings.cache.overwrite_eurostat
        if data_path.exists() != meta_path.exists() and not overwrite:
            existing = data_path if data_path.exists() else meta_path
            missing = meta_path if data_path.exists() else data_path
            raise ValueError(
                f"Eurostat cache '{name}' is incomplete: found '{existing}', but "
                f"'{missing}' is missing. Remove the incomplete cache or run with "
                "overwrite_eurostat enabled."
            )
        if data_path.exists() and meta_path.exists() and not overwrite:
            logger.info(f"Loading cached Eurostat data for '{name}' from {data_path}")
            frame = pd.read_feather(data_path)
            meta = json.loads(meta_path.read_text())
            frame = frame.set_index(list(frame.columns[: meta["n_index_levels"]]))
            if meta["columns_are_int"]:
                frame.columns = frame.columns.astype(int)
            if meta["is_series"]:
                return cast(pd.Series, frame.squeeze("columns"))
            return frame

        logger.info(f"Querying Eurostat for '{name}' (this may take a while)...")
        data = query()

        is_series = isinstance(data, pd.Series)
        columns_are_int = not is_series and all(
            isinstance(c, int) for c in data.columns
        )
        reset = data.reset_index()
        reset.columns = reset.columns.astype(str)

        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_temp_path = self._temporary_path(data_path)
        meta_temp_path = self._temporary_path(meta_path)
        try:
            reset.to_feather(data_temp_path)
            meta_temp_path.write_text(
                json.dumps(
                    {
                        "n_index_levels": data.index.nlevels,
                        "is_series": is_series,
                        "columns_are_int": columns_are_int,
                    }
                )
            )
            data_temp_path.replace(data_path)
            meta_temp_path.replace(meta_path)
        finally:
            data_temp_path.unlink(missing_ok=True)
            meta_temp_path.unlink(missing_ok=True)
        return data

    @staticmethod
    def _temporary_path(path: Path) -> Path:
        """Return a unique temporary path beside a cache file."""
        return path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")

    @classmethod
    def _write_json_atomic(cls, path: Path, value: Any) -> None:
        """Write JSON without exposing a partially written cache file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = cls._temporary_path(path)
        try:
            temporary_path.write_text(json.dumps(value))
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _query_cache_key(self, dataset: str, filter_pars: dict[str, Any]) -> str:
        """Deterministic cache key for a Eurostat query, derived from its
        actual request parameters."""
        canonical = json.dumps(filter_pars, sort_keys=True, default=str)
        digest = hashlib.md5(canonical.encode()).hexdigest()[:12]
        return f"{dataset}_{digest}"

    # -------- outward-facing accessors ------------------

    @instance_cache
    def get_efficiencies(self) -> pd.Series:
        """Fleet efficiency (output/input) per technology, at the latest
        available Eurostat year."""
        return self._query_efficiencies()

    @instance_cache
    def get_electricity_generation(self) -> pd.Series:
        """Gross electricity generation per country, at the latest
        available Eurostat year."""
        return self._query_electricity_generation()

    @instance_cache
    def get_total_heat_household(self) -> pd.DataFrame:
        """Heat consumption per node."""
        return self._query_total_heat_household()

    @instance_cache
    def get_heat_household_technology(self) -> pd.DataFrame:
        """Household heat consumption per technology/node."""
        return self._query_heat_household_technology()

    @instance_cache
    def get_heat_dh_technology(self) -> pd.DataFrame:
        """District heat consumption per technology/node."""
        return self._query_heat_dh_technology()

    @instance_cache
    def get_coal_availability(self) -> pd.DataFrame:
        """Coal availability per node."""
        return self._query_coal_availability()

    @instance_cache
    def get_oil_availability(self) -> pd.Series:
        """Oil availability per node."""
        return self._query_oil_availability()

    @instance_cache
    def get_natural_gas_production(self) -> pd.DataFrame:
        """Natural gas production per node."""
        return self._query_natural_gas_production()

    @instance_cache
    def get_waste_availability(self, include_industry: bool = False) -> pd.Series:
        """Waste availability per node.

        Args:
            include_industry: Whether to include industrial waste
                consumption in the availability calculation.
        """
        return self._query_waste_availability(include_industry=include_industry)

    @instance_cache
    def get_naphtha_demand(self) -> pd.DataFrame:
        """Naphtha demand per node."""
        return self._query_naphtha_demand()

    @instance_cache
    def get_kerosene_demand(self) -> pd.DataFrame:
        """Kerosene demand per node."""
        return self._query_kerosene_demand()

    @instance_cache
    def get_shipping_fuel_demand(self) -> pd.Series:
        """Shipping fuel demand per node."""
        return self._query_shipping_fuel_demand()

    @instance_cache
    def get_population_by_urbanization(self) -> pd.DataFrame:
        """Population share per country and degree of urbanization (urban,
        intermediate, rural), for all available Eurostat years."""
        return self._query_population_by_urbanization()

    # -------- data queries ------------------

    def _query_efficiencies(self) -> pd.Series:
        """Compute fleet efficiencies of power plants/carriers.

        Calculated as output/input for electricity-only technologies.
        """
        efficiencies = self._query_siec_data(
            nrg_bal=_EFFICIENCY_NRG_BAL,
            siec=_EFFICIENCY_SIEC,
            start_period=_EUROSTAT_START_YEAR,
        )
        efficiencies = cast(
            pd.DataFrame,
            efficiencies.drop(["freq", "unit"], axis=1)
            .set_index(["nrg_bal", "geo\\TIME_PERIOD", "siec"])
            .squeeze(),
        )
        efficiencies = efficiencies.ffill(axis=1)
        efficiencies.columns = efficiencies.columns.astype(int)
        efficiencies = efficiencies[self.eurostat_year].unstack()
        efficiencies = efficiencies.groupby(level=0).sum()
        efficiencies = (
            efficiencies.rename(_EFFICIENCY_NRG_BAL, axis=0)
            .rename(_EFFICIENCY_SIEC, axis=1)
            .rename(_EFFICIENCY_TECHNOLOGY_NAMES, axis=1)
        )
        return efficiencies.loc["output"] / efficiencies.loc["input"]

    def _query_electricity_generation(self) -> pd.Series:
        """Extract the gross electricity generation from Eurostat."""
        siec = {"TOTAL": "Total"}
        nrg_bal = {"GEP": "Gross electricity production"}
        generation = self._query_siec_data(
            nrg_bal=nrg_bal,
            siec=siec,
            start_period=self.eurostat_time_series_year,
        )
        generation = cast(
            pd.DataFrame,
            generation.drop(["freq", "unit", "nrg_bal", "siec"], axis=1)
            .set_index("geo\\TIME_PERIOD")
            .squeeze(),
        )
        generation = generation.astype(float)
        generation.columns = generation.columns.astype(int)
        generation = generation[self.eurostat_time_series_year]
        return generation.sort_index()

    def _query_total_heat_household(self) -> pd.DataFrame:
        """Load total Eurostat household-electricity heat data for NO + UK."""
        heat_data = self._query_siec_data(
            nrg_bal=_HEAT_HOUSEHOLD_NRG_BAL,
            siec=_HEAT_HOUSEHOLD_SIEC_TOTAL,
            start_period=_EUROSTAT_START_YEAR,
            dataset=_HEAT_HOUSEHOLD_DATASET,
            unit=_HEAT_HOUSEHOLD_UNIT,
            geo=["NO", "UK"],
        )
        heat_data = self._convert_availability(
            heat_data,
            _HEAT_HOUSEHOLD_SIEC_TOTAL,
            cutoff_year=self.eurostat_time_series_year,
        )
        heat_data = heat_data.rename(index=_HEAT_HOUSEHOLD_NRG_BAL, level=0)
        heat_data = heat_data.swaplevel(0, 1).sort_index(level=0)
        return heat_data / Constants.GJ_PER_MWH  # convert from TJ to GWh

    def _query_heat_household_technology(self) -> pd.DataFrame:
        """Load Eurostat household heat data."""
        heat_data = self._query_siec_data(
            nrg_bal=_HEAT_HOUSEHOLD_NRG_BAL,
            siec=_HEAT_HOUSEHOLD_SIEC,
            start_period=_EUROSTAT_START_YEAR,
            dataset=_HEAT_HOUSEHOLD_DATASET,
            unit=_HEAT_HOUSEHOLD_UNIT,
        )
        heat_data = self._convert_availability(
            heat_data, _HEAT_HOUSEHOLD_SIEC, return_all_years=True
        )
        heat_data = heat_data.rename(index=_HEAT_HOUSEHOLD_NRG_BAL, level=0)
        heat_data = heat_data.rename(index=_HEAT_HOUSEHOLD_SIEC, level=2)
        heat_data = heat_data.groupby(level=[1, 2]).sum(numeric_only=True)
        heat_data = heat_data.swaplevel(0, 1).sort_index()
        return heat_data / Constants.GJ_PER_MWH  # convert from TJ to GWh

    def _query_heat_dh_technology(self) -> pd.DataFrame:
        """Load Eurostat district heat data."""
        heat_data = self._query_siec_data(
            nrg_bal=_HEAT_DH_NRG_BAL,
            siec=_HEAT_DH_SIEC,
            start_period=_EUROSTAT_START_YEAR,
            unit=_HEAT_HOUSEHOLD_UNIT,
        )
        heat_data = self._convert_availability(
            heat_data, _HEAT_DH_SIEC, return_all_years=True
        )
        heat_data = heat_data.rename(index=_HEAT_DH_NRG_BAL, level=0)
        heat_data = heat_data.rename(index=_HEAT_DH_SIEC, level=2)
        heat_data = heat_data.groupby(level=[1, 2]).sum(numeric_only=True)
        heat_data = heat_data.swaplevel(0, 1).sort_index()
        return heat_data / Constants.GJ_PER_MWH  # convert from TJ to GWh

    def _query_coal_availability(self) -> pd.DataFrame:
        """Calculate coal availability, scaled from imports and production
        by the ratio of total consumption to total availability."""
        data = self._query_siec_data(
            nrg_bal=_COAL_NRG_BAL, siec=_COAL_SIEC, start_period=self.eurostat_year
        )
        data = self._convert_availability(data, _COAL_SIEC)
        imports = cast(pd.DataFrame, data.loc["IMP"])
        production = cast(pd.DataFrame, data.loc["PPRD"])
        availability = imports + production
        availability = availability.fillna(0)
        availability.index.name = "node"
        return availability.sort_index()

    def _query_natural_gas_production(self) -> pd.DataFrame:
        """Calculate natural gas production."""
        data = self._query_siec_data(
            nrg_bal=_NATURAL_GAS_NRG_BAL,
            siec=_NATURAL_GAS_SIEC,
            start_period=self.eurostat_year,
        )
        data = self._convert_availability(data, _NATURAL_GAS_SIEC)
        production = data.groupby(level=1).sum(numeric_only=True)
        return production.sort_index()

    def _query_biomass_availability(self) -> pd.Series:
        """Calculate biomass availability from transformation input and
        final consumption (households and commercial)."""
        data = self._query_siec_data(
            nrg_bal=_BIOMASS_NRG_BAL,
            siec=_BIOMASS_SIEC,
            start_period=self.eurostat_year,
        )
        data = self._convert_availability(data, _BIOMASS_SIEC)
        transformation_input = cast(pd.DataFrame, data.loc["TI_EHG_E"]).sum(axis=1)
        final_consumption_households = cast(pd.DataFrame, data.loc["FC_OTH_HH_E"]).sum(
            axis=1
        )
        final_consumption_commercial = cast(pd.DataFrame, data.loc["FC_OTH_CP_E"]).sum(
            axis=1
        )
        availability = (
            transformation_input
            + final_consumption_commercial
            + final_consumption_households
        )
        return availability.sort_index()

    def _query_oil_availability(self) -> pd.Series:
        """Calculate oil availability from transformation input and final
        consumption (households and commercial)."""
        data = self._query_siec_data(
            nrg_bal=_OIL_NRG_BAL, siec=_OIL_SIEC, start_period=self.eurostat_year
        )
        data = self._convert_availability(data, _OIL_SIEC)
        availability = data.groupby(level=1).sum(numeric_only=True).sum(axis=1)
        return availability.sort_index()

    def _query_waste_availability(self, include_industry: bool = False) -> pd.Series:
        """Calculate waste availability from transformation input and final
        consumption (households, commercial, and optionally industry)."""
        nrg_bal = dict(_WASTE_NRG_BAL)
        if include_industry:
            nrg_bal.update(_WASTE_INDUSTRY_NRG_BAL)
        data = self._query_siec_data(
            nrg_bal=nrg_bal, siec=_WASTE_SIEC, start_period=self.eurostat_year
        )
        data = self._convert_availability(data, _WASTE_SIEC)
        availability = data.astype(float).groupby(level=1).sum().sum(axis=1)
        return availability.sort_index()

    def _query_naphtha_demand(self) -> pd.DataFrame:
        """Calculate naphtha demand from transformation output."""
        data = self._query_siec_data(
            nrg_bal=_NAPHTHA_NRG_BAL,
            siec=_NAPHTHA_SIEC,
            start_period=self.eurostat_year,
        )
        data = self._convert_availability(data, _NAPHTHA_SIEC, return_all_years=True)
        demand = data.groupby(level=1).sum(numeric_only=True)
        demand.columns = demand.columns.astype(int)
        return demand.sort_index()

    def _query_kerosene_demand(self) -> pd.DataFrame:
        """Calculate kerosene demand from international and domestic
        aviation consumption."""
        data = self._query_siec_data(
            nrg_bal=_KEROSENE_NRG_BAL,
            siec=_KEROSENE_SIEC,
            start_period=self.eurostat_year,
        )
        data = self._convert_availability(data, _KEROSENE_SIEC)
        demand = data.groupby(level=1).sum(numeric_only=True)
        return demand.sort_index()

    def _query_shipping_fuel_demand(self) -> pd.Series:
        """Calculate shipping fuel demand from international and domestic
        navigation consumption."""
        data = self._query_siec_data(
            nrg_bal=_SHIPPING_FUEL_NRG_BAL,
            siec=_SHIPPING_FUEL_SIEC,
            start_period=self.eurostat_year,
        )
        data = self._convert_availability(data, _SHIPPING_FUEL_SIEC)
        demand = data.groupby(level=1).sum(numeric_only=True).sum(axis=1)
        return demand.sort_index()

    def _query_population_by_urbanization(self) -> pd.DataFrame:
        """Extract population by degree of urbanization from Eurostat."""
        population = self._query_urbanization_data(
            risk_of_pov=_URBANIZATION_RISK_OF_POVERTY,
            building=_URBANIZATION_TYPE_OF_BUILDING,
            deg_urb=_URBANIZATION_DEGREE,
            start_period=_EUROSTAT_START_YEAR,
        )
        population = population.drop(
            ["freq", "rskpovth", "building", "unit"], axis=1
        ).set_index(["deg_urb", "geo\\TIME_PERIOD"])
        population.columns = population.columns.astype(int)
        population = population.rename(_URBANIZATION_DEGREE, axis=0)
        population.index.names = ["deg_urb", "geo"]
        population = population.bfill(axis=1).ffill(axis=1)
        return population.sort_index() / 100

    def _convert_availability(
        self,
        data: pd.DataFrame,
        siec: dict[str, str],
        use_max: bool = False,
        return_all_years: bool = False,
        cutoff_year: int | None = None,
    ) -> pd.DataFrame:
        """Reshape a raw Eurostat siec query result into an
        availability/consumption table, limited to the given cutoff year."""
        if cutoff_year is None:
            cutoff_year = self.eurostat_year
        data = cast(
            pd.DataFrame,
            data.drop(["freq", "unit"], axis=1)
            .set_index(["nrg_bal", "geo\\TIME_PERIOD", "siec"])
            .squeeze(),
        )
        data = data.loc[:, data.columns.astype(int) <= cutoff_year]
        data = data.ffill(axis=1)
        if not return_all_years:
            if not use_max:
                data = data[str(cutoff_year)].unstack()
            else:
                data = data.max(axis=1).unstack()
            data = data.rename(siec, axis=1)
        return data

    # -------- generic Eurostat query helpers ------------------

    def _query_siec_data(
        self,
        nrg_bal: dict[str, str],
        siec: dict[str, str],
        start_period: int,
        geo: list[str] | None = None,
        dataset: str = "nrg_bal_c",
        unit: str = "GWH",
    ) -> pd.DataFrame:
        """Query the Eurostat energy-balance API, filtered by siec/nrg_bal.

        Cached to disk since Eurostat queries are slow; the cache key is
        derived from the actual request parameters.
        """
        filter_pars: dict[str, Any] = {"start_period": start_period, "unit": unit}

        eurostat_countries = self._get_par_values(dataset, "geo")
        common_geo = sorted(
            set(geo or eurostat_countries).intersection(eurostat_countries)
        )
        assert common_geo, f"None of the locations {geo} are in Eurostat database"
        filter_pars["geo"] = common_geo

        common_siec = sorted(
            set(self._get_par_values(dataset, "siec")).intersection(siec)
        )
        assert common_siec, f"None of the siec {siec} are in Eurostat database"
        filter_pars["siec"] = common_siec

        common_bal = sorted(
            set(self._get_par_values(dataset, "nrg_bal")).intersection(nrg_bal)
        )
        assert common_bal, f"None of the nrg_bal {nrg_bal} are in Eurostat database"
        filter_pars["nrg_bal"] = common_bal

        return cast(
            pd.DataFrame,
            self._cached_query(
                self._query_cache_key(dataset, filter_pars),
                lambda: self._query_in_parallel(
                    filter_pars,
                    common_geo,
                    dataset,
                    required_geo=common_geo if geo is not None else None,
                ),
            ),
        )

    def _query_non_siec_data(
        self,
        dataset: str,
        unit: str,
        start_period: int,
        geo: list[str] | None = None,
        params: dict[str, list[str]] | None = None,
    ) -> pd.DataFrame:
        """Query a Eurostat dataset that has no siec dimension.

        Cached to disk since Eurostat queries are slow; the cache key is
        derived from the actual request parameters.

        TODO: understand if still required even without the eurostat vehicle dataset
        """
        filter_pars: dict[str, Any] = {"start_period": start_period, "unit": unit}

        eurostat_countries = self._get_par_values(dataset, "geo")
        common_geo = sorted(
            set(geo or eurostat_countries).intersection(eurostat_countries)
        )
        assert common_geo, f"None of the locations {geo} are in Eurostat database"
        filter_pars["geo"] = common_geo

        for param, values in (params or {}).items():
            common_param = sorted(
                set(self._get_par_values(dataset, param)).intersection(values)
            )
            assert (
                common_param
            ), f"None of the param {param} ({values}) are in Eurostat database"
            filter_pars[param] = common_param

        return cast(
            pd.DataFrame,
            self._cached_query(
                self._query_cache_key(dataset, filter_pars),
                lambda: self._query_in_parallel(
                    filter_pars,
                    common_geo,
                    dataset,
                    required_geo=common_geo if geo is not None else None,
                ),
            ),
        )

    def _query_urbanization_data(
        self,
        risk_of_pov: dict[str, str],
        building: dict[str, str],
        deg_urb: dict[str, str],
        start_period: int,
        geo: list[str] | None = None,
        dataset: str = _URBANIZATION_DATASET,
    ) -> pd.DataFrame:
        """Query the Eurostat urt_pjanaggr3 API (population by degree of
        urbanization), filtered by risk_of_pov/building/deg_urb.

        Cached to disk since Eurostat queries are slow; the cache key is
        derived from the actual request parameters.
        """
        filter_pars: dict[str, Any] = {"start_period": start_period}

        eurostat_countries = self._get_par_values(dataset, "geo")
        common_geo = sorted(
            set(geo or eurostat_countries).intersection(eurostat_countries)
        )
        assert common_geo, f"None of the locations {geo} are in Eurostat database"
        filter_pars["geo"] = common_geo

        common_risk_of_pov = sorted(
            set(self._get_par_values(dataset, "rskpovth")).intersection(risk_of_pov)
        )
        assert (
            common_risk_of_pov
        ), f"None of the risk_of_pov {risk_of_pov} are in Eurostat database"
        filter_pars["rskpovth"] = common_risk_of_pov

        common_building = sorted(
            set(self._get_par_values(dataset, "building")).intersection(building)
        )
        assert (
            common_building
        ), f"None of the building {building} are in Eurostat database"
        filter_pars["building"] = common_building

        common_deg_urb = sorted(
            set(self._get_par_values(dataset, "deg_urb")).intersection(deg_urb)
        )
        assert common_deg_urb, f"None of the deg_urb {deg_urb} are in Eurostat database"
        filter_pars["deg_urb"] = common_deg_urb

        return cast(
            pd.DataFrame,
            self._cached_query(
                self._query_cache_key(dataset, filter_pars),
                lambda: self._query_in_parallel(
                    filter_pars,
                    common_geo,
                    dataset,
                    required_geo=common_geo if geo is not None else None,
                ),
            ),
        )

    def _query_in_parallel(
        self,
        filter_pars: dict[str, Any],
        geo: list[str],
        dataset: str,
        required_geo: list[str] | None = None,
    ) -> pd.DataFrame:
        """Query and validate a Eurostat dataset, one request per country.

        Args:
            filter_pars: Filters shared by all country requests.
            geo: Countries or regions to query.
            dataset: Eurostat dataset identifier.
            required_geo: Explicitly requested locations that must return rows.

        Returns:
            Combined, validated Eurostat response.

        Raises:
            ValueError: If the combined response is empty, malformed, or omits an
                explicitly requested location.
        """
        filter_pars_per_geo = [(filter_pars, single_geo, dataset) for single_geo in geo]
        if not filter_pars_per_geo:
            raise ValueError(
                f"No Eurostat locations were selected for dataset '{dataset}'."
            )

        logger.info("Start Eurostat pool")
        worker_count = min(_MAX_QUERY_WORKERS, len(filter_pars_per_geo))
        if worker_count == 1:
            results = [
                self._extract_single_country(arguments)
                for arguments in filter_pars_per_geo
            ]
        else:
            with mp.Pool(worker_count) as pool:
                results = pool.map(self._extract_single_country, filter_pars_per_geo)
        logger.info("End Eurostat pool")

        non_empty_results = [result for result in results if not result.empty]
        if not non_empty_results:
            raise ValueError(
                f"Eurostat dataset '{dataset}' returned no data for the requested "
                f"period {filter_pars['start_period']}."
            )

        data = pd.concat(non_empty_results)
        year_columns = pd.Index(
            [column for column in data.columns if str(column).isdigit()]
        )
        data[year_columns] = data[year_columns].apply(pd.to_numeric, errors="coerce")
        self._validate_query_result(data, filter_pars, dataset, required_geo or [])
        return data

    def _extract_single_country(
        self, args: tuple[dict[str, Any], str, str]
    ) -> pd.DataFrame:
        """Extract Eurostat data for a single country.

        Data for the United Kingdom is not always available for the most
        recent years; in that case, fall back to querying two years earlier
        and relabel the result to the originally requested year.
        """
        filter_pars, geo, dataset = args
        filter_pars = dict(filter_pars, geo=geo)
        requested_period = filter_pars["start_period"]

        if geo == "UK" and requested_period > _LAST_EUROSTAT_YEAR_UK:
            filter_pars["start_period"] = _LAST_EUROSTAT_YEAR_UK

        result = self._query_country_with_retries(dataset, geo, filter_pars)
        if geo == "UK" and requested_period > _LAST_EUROSTAT_YEAR_UK:
            result = result.rename({_LAST_EUROSTAT_YEAR_UK: requested_period}, axis=1)
        return result

    @staticmethod
    def _query_country_with_retries(
        dataset: str, geo: str, filter_pars: dict[str, Any]
    ) -> pd.DataFrame:
        """Query one country, retrying temporary errors and empty responses."""
        context = Eurostat._query_context(dataset, geo, filter_pars)
        for attempt in range(1, _QUERY_ATTEMPTS + 1):
            if attempt > 1:
                time.sleep(attempt - 1)
            try:
                result = es.get_data_df(dataset, filter_pars=filter_pars)
            except requests.RequestException:
                if attempt == _QUERY_ATTEMPTS:
                    logger.warning(
                        f"Eurostat request failed after {_QUERY_ATTEMPTS} attempts: "
                        f"{context}."
                    )
                    raise
                logger.warning(
                    f"Retrying Eurostat request for {context} "
                    f"({attempt + 1}/{_QUERY_ATTEMPTS})."
                )
                continue

            if result is not None and not result.empty:
                return result
            if attempt < _QUERY_ATTEMPTS:
                logger.warning(
                    f"Retrying empty Eurostat response for {context} "
                    f"({attempt + 1}/{_QUERY_ATTEMPTS})."
                )

        logger.warning(f"No Eurostat data found for {context}.")
        return pd.DataFrame()

    @staticmethod
    def _query_context(dataset: str, geo: str, filter_pars: dict[str, Any]) -> str:
        """Summarize one Eurostat request for concise warning messages."""
        details = []
        for key, value in filter_pars.items():
            if key == "geo":
                continue
            if isinstance(value, list) and len(value) > 3:
                details.append(f"{key}={len(value)} values")
            else:
                details.append(f"{key}={value}")
        return f"dataset '{dataset}' for {geo} ({', '.join(details)})"

    @staticmethod
    def _validate_query_result(
        data: pd.DataFrame,
        filter_pars: dict[str, Any],
        dataset: str,
        required_geo: list[str],
    ) -> None:
        """Validate a combined Eurostat response before it is cached."""
        geo_column = "geo\\TIME_PERIOD"
        expected_dimensions = set(filter_pars).difference({"start_period", "geo"})
        missing_columns = sorted(
            expected_dimensions.difference(data.columns)
            | ({geo_column} - set(data.columns))
        )
        if missing_columns:
            raise ValueError(
                f"Eurostat dataset '{dataset}' is missing expected columns: "
                f"{', '.join(missing_columns)}."
            )

        start_period = int(filter_pars["start_period"])
        period_columns = [
            column
            for column in data.columns
            if str(column).isdigit() and int(str(column)) >= start_period
        ]
        if not period_columns:
            raise ValueError(
                f"Eurostat dataset '{dataset}' has no year columns from requested "
                f"start period {start_period}."
            )

        numeric_values = data[period_columns].apply(pd.to_numeric, errors="coerce")
        if not numeric_values.notna().any(axis=None):
            raise ValueError(
                f"Eurostat dataset '{dataset}' contains no numeric values for "
                f"years from {start_period}."
            )

        returned_geo = set(data[geo_column].dropna().astype(str))
        missing_geo = sorted(set(required_geo).difference(returned_geo))
        if missing_geo:
            raise ValueError(
                f"Eurostat dataset '{dataset}' has no data for explicitly requested "
                f"locations: {', '.join(missing_geo)}."
            )

    @instance_cache
    def get_vehicle_occupancy(self) -> float:
        """Get the average vehicle occupancy.

        From https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Passenger_mobility_statistics#Passenger_car_occupancy

        Read from the plot
        """
        values = [
            1.873239419845443,
            1.7370892042322186,
            1.3826287732314277,
            1.3427226344836363,
            1.2793424070891761,
            1.2605630108062045,
            1.2535210976262958,
            1.2347414506120507,
            1.2230043436058982,
            1.2183095258765642,
            1.220657248155323,
            1.199530505690503,
            1.1619714623932864,
        ]
        return sum(values) / len(values)

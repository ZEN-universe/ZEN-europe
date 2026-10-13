from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import ClassVar

from zen_creator.utils.settings import SettingsCategory


class CacheSettings(SettingsCategory):
    """Settings controlling which dataset caches are reloaded from source and
    overwritten on disk, instead of being read from an existing cache file."""

    name: ClassVar[str] = "cache"

    overwrite_dea: bool = False
    overwrite_entsoe: bool = False
    overwrite_eurostat: bool = False
    overwrite_eea_ghg_inventory: bool = False
    overwrite_global_carbon_budget: bool = False
    overwrite_desnz_ghg_inventory: bool = False
    overwrite_worldbank_co2_emissions: bool = False
    overwrite_worldbank_population: bool = False
    overwrite_ecb: bool = False
    overwrite_jrc_idees: bool = False
    overwrite_unece: bool = False
    overwrite_pan_european_climate_database: bool = False
    overwrite_passenger_cars_cox: bool = False
    overwrite_glohydrores: bool = False
    overwrite_jrc_hydro_power_database: bool = False
    overwrite_pecd_hydro_capacities: bool = False
    overwrite_powerplantmatching: bool = False


class CacheArtifactKind(str, Enum):
    """Classification of files used or produced during model generation."""

    IMMUTABLE_SOURCE = "immutable_checked_in_source"
    DOWNLOADED_SOURCE = "downloaded_source_snapshot"
    DERIVED_CACHE = "derived_cache"
    MODEL_OUTPUT = "model_output"


@dataclass(frozen=True)
class CacheProvider:
    """Files owned by one dataset cache provider, relative to source_path."""

    name: str
    kind: CacheArtifactKind
    patterns: tuple[str, ...]


# Immutable checked-in sources and model outputs are deliberately absent: they are
# classified above, but never cache-deletion targets. Every entry below is produced
# by ZEN-europe from a remote source or another local input.
CACHE_PROVIDERS = (
    CacheProvider(
        "entsoe",
        CacheArtifactKind.DOWNLOADED_SOURCE,
        ("02-carrier/entsoe/*.feather", "02-carrier/entsoe/*.json"),
    ),
    CacheProvider(
        "eurostat",
        CacheArtifactKind.DOWNLOADED_SOURCE,
        ("02-carrier/eurostat/*.feather", "02-carrier/eurostat/*.json"),
    ),
    CacheProvider(
        "dea",
        CacheArtifactKind.DOWNLOADED_SOURCE,
        (
            "03-technology/cost/dea/technology_data_for_el_and_dh.xlsx",
            "03-technology/cost/dea/technology_data_heating_installations.xlsx",
            "03-technology/cost/dea/data_sheets_for_renewable_fuels.xlsx",
            "03-technology/cost/dea/technology_data_for_carbon_capture_transport_storage.xlsx",
            "03-technology/cost/dea/technology_data_for_energy_transport.xlsx",
        ),
    ),
    CacheProvider(
        "dea",
        CacheArtifactKind.DERIVED_CACHE,
        ("03-technology/cost/dea/dea_processed.feather",),
    ),
    CacheProvider(
        "ecb",
        CacheArtifactKind.DOWNLOADED_SOURCE,
        ("04-monetary/ecb/ecb_inflation.csv", "04-monetary/ecb/ecb_dollar_to_euro.csv"),
    ),
    CacheProvider(
        "greenhouse_gas_and_worldbank",
        CacheArtifactKind.DERIVED_CACHE,
        (
            "01-energy_system/desnz_ghg_inventory/*.csv",
            "01-energy_system/eea_ghg_inventory/*.csv",
            "01-energy_system/global_carbon_budget/*.csv",
            "01-energy_system/worldbank_co2_emissions/*.csv",
            "01-energy_system/worldbank_population/*.csv",
        ),
    ),
    CacheProvider(
        "jrc_idees",
        CacheArtifactKind.DERIVED_CACHE,
        ("02-carrier/heat/jrc_idees/useful_thermal_energy_service.feather",),
    ),
    CacheProvider(
        "unece",
        CacheArtifactKind.DOWNLOADED_SOURCE,
        ("03-technology/capacity_existing/transport/unece/*.feather",),
    ),
    CacheProvider(
        "pan_european_climate_database",
        CacheArtifactKind.DOWNLOADED_SOURCE,
        (
            "03-technology/climate_data/*_raw.zip",
            "03-technology/climate_data/onshore_wind_weights.csv",
            "03-technology/climate_data/offshore_wind_weights.csv",
        ),
    ),
    CacheProvider(
        "pan_european_climate_database",
        CacheArtifactKind.DERIVED_CACHE,
        ("03-technology/climate_data/pecd_data_*.feather",),
    ),
    CacheProvider(
        "passenger_cars_cox",
        CacheArtifactKind.DERIVED_CACHE,
        ("03-technology/passenger_cars/vehicle_tech_parameters.csv",),
    ),
    CacheProvider(
        "glohydrores",
        CacheArtifactKind.DERIVED_CACHE,
        (
            "03-technology/capacity_existing/glohydrores_data.feather",
            "03-technology/capacity_existing/glohydrores_data_raw.feather",
        ),
    ),
    CacheProvider(
        "jrc_hydro_power_database",
        CacheArtifactKind.DOWNLOADED_SOURCE,
        ("03-technology/capacity_existing/jrc_hydro_power_database_data.feather",),
    ),
    CacheProvider(
        "pecd_hydro_capacities",
        CacheArtifactKind.DOWNLOADED_SOURCE,
        ("03-technology/capacity_existing/PECD-hydro-capacities.csv",),
    ),
    CacheProvider(
        "powerplantmatching",
        CacheArtifactKind.DERIVED_CACHE,
        (
            "03-technology/capacity_existing/processed_powerplantmatching_data_raw.feather",
        ),
    ),
)


def clear_caches(source_path: Path | str) -> list[Path]:
    """Delete all registered downloaded sources and derived caches.

    Args:
        source_path: Root directory containing ZEN-europe source data.

    Returns:
        Paths of the files that were removed.
    """
    root = Path(source_path).resolve()
    removed: list[Path] = []
    for provider in CACHE_PROVIDERS:
        for pattern in provider.patterns:
            for path in root.glob(pattern):
                resolved = path.resolve()
                if not resolved.is_relative_to(root):
                    raise ValueError(
                        f"Cache provider '{provider.name}' resolved a path outside "
                        f"source_path: {resolved}"
                    )
                if resolved.is_file():
                    resolved.unlink()
                    removed.append(resolved)
    return removed


_active = CacheSettings()


def set_active_cache_settings(settings: CacheSettings) -> None:
    """Set the process-wide cache settings that dataset cache checks read.

    Datasets that receive `settings` directly (e.g. via dependency injection)
    can read `settings.cache` instead. This accessor is for datasets that do
    not, so that the overwrite flags do not have to be threaded through every
    dataset constructor and call site.
    """
    global _active
    _active = settings


def get_active_cache_settings() -> CacheSettings:
    """Return the process-wide cache settings, defaulting to all-False."""
    return _active
